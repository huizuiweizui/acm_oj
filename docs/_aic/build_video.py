"""合成演示视频：旁白（edge-tts，失败时用 Windows 慧慧）+ 幻灯片 / 录屏 + 字幕与场景标签。

    python build_video.py [--no-llm] [--out 星语-演示视频.mp4]
依赖：ffmpeg（含 libass）、edge_tts（PYTHONPATH 指向 pylib）、clips/ 与 slides/ 已生成。
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

from narration import NO_LLM_NOTE, SEGMENTS

HERE = Path(__file__).resolve().parent
TTS = HERE / 'tts'
SEG = HERE / 'seg'
VOICE = 'zh-CN-XiaoxiaoNeural'
RATE = '+4%'
FPS = 30
LEAD = 0.5        # 每段画面出现后旁白延迟开始
TAIL = 0.9        # 旁白结束后多停一会
SUB_MAX = 24      # 每条字幕最多字数


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', **kw)
    if r.returncode:
        sys.exit(f'命令失败：{" ".join(map(str, cmd))[:300]}\n{r.stderr[-2000:]}')
    return r.stdout


def probe(path):
    return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)]).strip())


# ── 旁白 ────────────────────────────────────────────────────────────
async def edge(text, mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary='SentenceBoundary')
    cues = []
    with open(mp3, 'wb') as f:
        async for ch in comm.stream():
            if ch['type'] == 'audio':
                f.write(ch['data'])
            elif ch['type'] == 'SentenceBoundary':
                cues.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']))
    return cues


def sapi(text, mp3):
    wav = mp3.with_suffix('.wav')
    ps = ('Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; '
          f'$s.SelectVoice("Microsoft Huihui Desktop"); $s.Rate=1; $s.SetOutputToWaveFile("{wav}"); '
          f'$s.Speak([IO.File]::ReadAllText("{mp3.with_suffix(".txt")}", [Text.Encoding]::UTF8)); $s.Dispose()')
    mp3.with_suffix('.txt').write_text(text, encoding='utf-8')
    run(['powershell', '-NoProfile', '-Command', ps])
    run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(wav), '-b:a', '160k', str(mp3)])
    return []


def split_long(cues, total):
    """句子级时间轴 → 字幕条：长句按标点切开，时间按字数分配。没有时间轴时按全文字数均分。"""
    out = []
    for start, end, text in cues:
        parts, buf = [], ''
        for piece in re.split(r'(?<=[，、；：。！？])', text):
            if buf and len(buf) + len(piece) > SUB_MAX:
                parts.append(buf); buf = ''
            buf += piece
        if buf:
            parts.append(buf)
        n = sum(len(p) for p in parts) or 1
        t = start
        for p in parts:
            d = (end - start) * len(p) / n
            out.append((t, t + d, p.strip('，、；： ')))
            t += d
    return out


def tts(seg, text):
    mp3 = TTS / f'{seg}.mp3'
    meta = TTS / f'{seg}.json'
    if meta.exists() and json.loads(meta.read_text(encoding='utf-8'))['text'] == text and mp3.exists():
        return json.loads(meta.read_text(encoding='utf-8'))
    try:
        cues = asyncio.run(edge(text, mp3))
        engine = 'edge'
    except Exception as e:  # 网络不通等
        print(f'  edge-tts 失败（{e}），改用慧慧')
        cues, engine = sapi(text, mp3), 'sapi'
    dur = probe(mp3)
    if not cues:
        sents = [s for s in re.split(r'(?<=[。！？])', text) if s]
        n, t = sum(map(len, sents)), 0.0
        for s in sents:
            d = dur * len(s) / n
            cues.append((t, t + d, s)); t += d
    data = dict(text=text, engine=engine, duration=dur, cues=split_long(cues, dur))
    meta.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    return data


# ── 画面 ────────────────────────────────────────────────────────────
def clip_duration(name):
    txt = (HERE / 'clips' / name / 'frames.txt').read_text()
    return sum(float(x) for x in re.findall(r'^duration (\S+)', txt, re.M))


def render_segment(i, seg, audio, dur):
    out = SEG / f'{i:02d}.mp4'
    kind, name = seg['visual'].split(':')
    fade = f'fade=t=in:st=0:d=0.35,fade=t=out:st={dur - 0.35:.2f}:d=0.35'
    if kind == 'slide':
        vin = ['-loop', '1', '-framerate', str(FPS), '-i', str(HERE / 'slides' / f'{name}.png')]
        vf = f'scale=1920:1080,format=yuv420p,{fade}'
    else:
        vin = ['-f', 'concat', '-safe', '0', '-i', str(HERE / 'clips' / name / 'frames.txt')]
        vf = (f'scale=1920:1080:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration={dur:.2f},'
              f'format=yuv420p,{fade}')
    delay = int(LEAD * 1000)
    run(['ffmpeg', '-y', '-loglevel', 'error', *vin, '-i', str(audio),
         '-filter_complex', f'[0:v]{vf}[v];[1:a]adelay={delay}|{delay},apad,aresample=48000[a]',
         '-map', '[v]', '-map', '[a]', '-t', f'{dur:.3f}', '-r', str(FPS),
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '192k', '-ac', '2', str(out)])
    return out


# ── 字幕（ASS）──────────────────────────────────────────────────────
ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Microsoft YaHei,46,&H00FFFFFF,&H00FFFFFF,&H64000000,&H8C101820,1,0,0,0,100,100,1,0,3,14,0,2,80,80,48,1
Style: Label,Microsoft YaHei,30,&H00FFFFFF,&H00FFFFFF,&H00A0602F,&H00A0602F,1,0,0,0,100,100,1,0,3,12,0,7,36,36,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ts(t):
    t = max(0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f'{int(h)}:{int(m):02d}:{s:05.2f}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-llm', action='store_true', help='录屏环境没接大模型：架构页旁白后加一句说明')
    ap.add_argument('--out', default=str(HERE / '星语-演示视频.mp4'))
    args = ap.parse_args()
    TTS.mkdir(exist_ok=True); SEG.mkdir(exist_ok=True)

    events, parts, t0 = [], [], 0.0
    for i, seg in enumerate(SEGMENTS):
        text = seg['text'] + (NO_LLM_NOTE if args.no_llm and seg['id'] == 's03' else '')
        a = tts(seg['id'], text)
        need = LEAD + a['duration'] + TAIL
        kind, name = seg['visual'].split(':')
        dur = max(need, clip_duration(name) + 0.3) if kind == 'clip' else need + 0.6
        print(f"{seg['id']} {seg['visual']:<18} 旁白 {a['duration']:5.1f}s  画面 {dur:5.1f}s  [{a['engine']}]")
        parts.append(render_segment(i, seg, TTS / f"{seg['id']}.mp3", dur))
        for s, e, txt in a['cues']:
            events.append(f'Dialogue: 0,{ts(t0 + LEAD + s)},{ts(t0 + LEAD + e)},Sub,,0,0,0,,{txt}')
        if seg['label']:
            events.append(f"Dialogue: 1,{ts(t0 + 0.3)},{ts(t0 + dur - 0.3)},Label,,0,0,0,,{seg['label']}")
        t0 += dur

    (HERE / 'subs.ass').write_text(ASS_HEAD + '\n'.join(events) + '\n', encoding='utf-8-sig')
    (SEG / 'list.txt').write_text(''.join(f"file '{p.name}'\n" for p in parts), encoding='utf-8')
    run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'seg/list.txt',
         '-vf', 'subtitles=subs.ass', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
         '-c:a', 'copy', '-movflags', '+faststart', args.out], cwd=HERE)
    print(f'完成：{args.out}  {probe(args.out):.1f}s')


if __name__ == '__main__':
    main()
