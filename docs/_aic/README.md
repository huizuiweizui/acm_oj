# 精英大赛材料的生成脚本

生成《作品方案》（套 2026AIC 模板）和演示视频。产物不进仓库，生成在本目录下（clips/、slides/、tts/、seg/、docshots/、out/）。

依赖：Node（用 `frontend/node_modules` 里的 playwright 和本机已装的 Chromium，路径写在 `lib.mjs`，可用环境变量 CHROME_PATH 覆盖），
ffmpeg（要带 libass），Python 包 python-docx、edge-tts，以及 Word（用来更新目录、导出 PDF）。

## 1. 准备演示环境（用演示库副本，不动 db.sqlite3）

```bash
cp db.sqlite3 <演示库>.sqlite3
export DB_ENGINE=sqlite DB_NAME=<演示库绝对路径>
python manage.py migrate
PYTHONPATH=. python docs/_aic/prep.py      # seed_star --reset-tasks，清空对话，删掉 star_newbie 的问卷
python manage.py runserver 127.0.0.1:8000
cd frontend && npx vite --port 5173
```

如果要录大模型的效果，启动后端前先设置 `LLM_API_KEY / LLM_API_URL / LLM_MODEL`。

## 2. 录屏与配图

```bash
node docs/_aic/record.mjs          # 7 段录屏，写到 clips/<场景>/；可只录某几段：node record.mjs steps chat
node docs/_aic/docshots.mjs        # 方案书配图（要在录屏之后跑，会用到录屏留下的作答记录）
node docs/_aic/render_slides.mjs   # slides.html → slides/*.png
```

## 3. 合成视频

```bash
python docs/_aic/build_video.py --no-llm     # 接了大模型的话去掉 --no-llm（架构页旁白会少一句说明）
```

旁白和分镜在 `narration.py` 里，TTS 结果按文本缓存在 tts/ 中，所以只改了某一段时，只会重新合成那一段。

## 4. 方案书

```bash
# 先用 Word 把模板 .doc 另存为 tpl.docx
python docs/_aic/build_aic.py tpl.docx out/aic.docx
powershell -File docs/_aic/finalize.ps1 -In <绝对路径>\out\aic.docx -Docx <...>\aic_final.docx -Pdf <...>\aic.pdf
```
