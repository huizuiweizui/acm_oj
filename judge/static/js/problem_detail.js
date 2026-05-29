/* ============================================
   题目详情页专用脚本
   Monaco Editor + 代码补全 + 测试面板 + 提交 + 渲染
   ============================================ */

// ==================== Monaco Editor 初始化 ====================
window.monacoEditor = null;

require.config({
    paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }
});

require(['vs/editor/editor.main'], function () {

    // ---------- 自定义主题（深色） ----------
    monaco.editor.defineTheme('acmoj-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'comment', foreground: '5c6478', fontStyle: 'italic' },
            { token: 'keyword', foreground: 'c084fc' },
            { token: 'string', foreground: '7dd3fc' },
            { token: 'number', foreground: '818cf8' },
            { token: 'type', foreground: 'fbbf24' },
            { token: 'function', foreground: '34d399' },
        ],
        colors: {
            'editor.background': '#0f1117',
            'editor.foreground': '#e8ecf4',
            'editor.lineHighlightBackground': '#171923',
            'editor.selectionBackground': '#364175',
            'editorLineNumber.foreground': '#3d4560',
            'editorLineNumber.activeForeground': '#8b93a7',
            'editorCursor.foreground': '#818cf8',
            'editor.inactiveSelectionBackground': '#1e2231',
            'editorIndentGuide.background': '#1e2231',
            'editorBracketMatch.background': '#34d39944',
            'editorBracketMatch.border': '#34d399',
        }
    });

    // ---------- 自定义主题（浅色） ----------
    monaco.editor.defineTheme('acmoj-light', {
        base: 'vs',
        inherit: true,
        rules: [
            { token: 'comment', foreground: '8b93a7', fontStyle: 'italic' },
            { token: 'keyword', foreground: '7c3aed' },
            { token: 'string', foreground: '0369a1' },
            { token: 'number', foreground: '4f46e5' },
            { token: 'type', foreground: 'b45309' },
            { token: 'function', foreground: '059669' },
        ],
        colors: {
            'editor.background': '#ffffff',
            'editor.foreground': '#1a1d2e',
            'editor.lineHighlightBackground': '#f5f6fa',
            'editorLineNumber.foreground': '#8b93a7',
            'editorLineNumber.activeForeground': '#1a1d2e',
            'editorCursor.foreground': '#4f46e5',
            'editorIndentGuide.background': '#edf0f7',
        }
    });

    // ---------- 语言模板 ----------
    var templates = {
        'C++': '#include <iostream>\n#include <vector>\n#include <algorithm>\nusing namespace std;\n\nint main() {\n    // 在此写下你的代码\n    \n    return 0;\n}',
        'C': '#include <stdio.h>\n#include <stdlib.h>\n\nint main() {\n    // 在此写下你的代码\n    \n    return 0;\n}',
        'Python': '# 在此写下你的代码\n',
        'Java': 'import java.util.*;\nimport java.io.*;\n\npublic class Main {\n    public static void main(String[] args) {\n        // 在此写下你的代码\n        \n    }\n}',
    };

    // 语言名映射到 Monaco language id
    var langMap = {
        'C++': 'cpp',
        'C': 'c',
        'Python': 'python',
        'Java': 'java',
    };

    var currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    var monacoTheme = currentTheme === 'dark' ? 'acmoj-dark' : 'acmoj-light';

    window.monacoEditor = monaco.editor.create(document.getElementById('monaco-editor'), {
        value: templates['C++'],
        language: 'cpp',
        theme: monacoTheme,
        fontSize: 14,
        fontFamily: "'JetBrains Mono', Consolas, monospace",
        fontLigatures: true,
        minimap: { enabled: true, scale: 0.8 },
        automaticLayout: true,
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        tabSize: 4,
        insertSpaces: true,
        renderLineHighlight: 'all',
        cursorBlinking: 'smooth',
        cursorSmoothCaretAnimation: 'on',
        smoothScrolling: true,
        formatOnPaste: true,
        formatOnType: true,
        bracketPairColorization: { enabled: true },
        guides: { bracketPairs: true, indentation: true },
    });

    // ---------- C++ 竞赛代码补全 ----------
    var cppItems = [
        { label: 'cin', kind: monaco.languages.CompletionItemKind.Function, insertText: 'cin >> ${1:var};', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'cout', kind: monaco.languages.CompletionItemKind.Function, insertText: 'cout << ${1:val} << endl;', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'forr', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n    $0\n}', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'ford', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'for (int ${1:i} = ${2:n} - 1; ${1:i} >= 0; ${1:i}--) {\n    $0\n}', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'while', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'while (${1:condition}) {\n    $0\n}', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'vec', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'vector<${1:int}> ${2:v};', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'vec2d', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'vector<vector<${1:int}>> ${2:v}(${3:n}, vector<${1:int}>(${4:m}));', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'sort', kind: monaco.languages.CompletionItemKind.Function, insertText: 'sort(${1:v}.begin(), ${1:v}.end());', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'main', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'int main() {\n    ${1}\n    return 0;\n}', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'io_sync_off', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'ios::sync_with_stdio(false);\ncin.tie(nullptr);', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'INF', kind: monaco.languages.CompletionItemKind.Constant, insertText: 'const int INF = 0x3f3f3f3f;' },
        { label: 'll', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'typedef long long ll;' },
        { label: 'pii', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'typedef pair<int, int> pii;' },
        { label: 'pb', kind: monaco.languages.CompletionItemKind.Snippet, insertText: '${1:v}.push_back(${2:val});', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
    ];

    monaco.languages.registerCompletionItemProvider('cpp', {
        provideCompletionItems: function (model, position) {
            var word = model.getWordUntilPosition(position);
            var range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn
            };
            return { suggestions: cppItems.map(function (item) { return Object.assign({}, item, { range: range }); }) };
        }
    });

    // ---------- Python 竞赛代码补全 ----------
    var pyItems = [
        { label: 'read_int', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'n = int(input())' },
        { label: 'read_ints', kind: monaco.languages.CompletionItemKind.Snippet, insertText: '${1:a}, ${2:b} = map(int, input().split())', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'read_list', kind: monaco.languages.CompletionItemKind.Snippet, insertText: '${1:a} = list(map(int, input().split()))', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'forr', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'for ${1:i} in range(${2:n}):\n    $0', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'main_guard', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'if __name__ == "__main__":\n    $0', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'sys_stdin', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'import sys\ninput = sys.stdin.readline' },
    ];

    monaco.languages.registerCompletionItemProvider('python', {
        provideCompletionItems: function (model, position) {
            var word = model.getWordUntilPosition(position);
            var range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn
            };
            return { suggestions: pyItems.map(function (item) { return Object.assign({}, item, { range: range }); }) };
        }
    });

    // ---------- Java 补全 ----------
    var javaItems = [
        { label: 'scanner', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'Scanner sc = new Scanner(System.in);', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'sout', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'System.out.println(${1:});', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
        { label: 'forr', kind: monaco.languages.CompletionItemKind.Snippet, insertText: 'for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n    $0\n}', insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet },
    ];

    monaco.languages.registerCompletionItemProvider('java', {
        provideCompletionItems: function (model, position) {
            var word = model.getWordUntilPosition(position);
            var range = {
                startLineNumber: position.lineNumber,
                endLineNumber: position.lineNumber,
                startColumn: word.startColumn,
                endColumn: word.endColumn
            };
            return { suggestions: javaItems.map(function (item) { return Object.assign({}, item, { range: range }); }) };
        }
    });

    // ---------- 语言切换 ----------
    var langSelect = document.getElementById('language-select');
    langSelect.addEventListener('change', function () {
        var lang = this.value;
        var monacoLang = langMap[lang] || 'cpp';
        var model = window.monacoEditor.getModel();
        monaco.editor.setModelLanguage(model, monacoLang);

        // 如果当前代码是模板或空，自动切换模板
        var currentCode = window.monacoEditor.getValue().trim();
        var isTemplate = Object.values(templates).some(function (t) { return currentCode === t.trim(); });
        if (currentCode === '' || isTemplate) {
            window.monacoEditor.setValue(templates[lang] || '');
        }
    });

    // ---------- 行数统计 ----------
    function updateLineCount() {
        var lineCount = window.monacoEditor.getModel().getLineCount();
        document.getElementById('line-count').textContent = lineCount + ' 行';
    }
    updateLineCount();
    window.monacoEditor.onDidChangeModelContent(updateLineCount);

    // ---------- 同步代码到隐藏 textarea ----------
    window.monacoEditor.onDidChangeModelContent(function () {
        document.getElementById('code-editor').value = window.monacoEditor.getValue();
    });
    document.getElementById('code-editor').value = window.monacoEditor.getValue();

    // ---------- 监听主题切换，动态更新 Monaco 主题 ----------
    var observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (m) {
            if (m.attributeName === 'data-theme') {
                var theme = document.documentElement.getAttribute('data-theme');
                monaco.editor.setTheme(theme === 'dark' ? 'acmoj-dark' : 'acmoj-light');
            }
        });
    });
    observer.observe(document.documentElement, { attributes: true });
});


// ==================== 提交评测 ====================
document.addEventListener('DOMContentLoaded', function () {
    var submitBtn = document.getElementById('submit-btn');
    if (!submitBtn) return;

    submitBtn.addEventListener('click', function () {
        var code = window.monacoEditor ? window.monacoEditor.getValue() : '';
        if (!code.trim()) {
            showToastLocal('请先输入代码', 'warning');
            return;
        }

        var url = this.dataset.url;
        if (!url) return;

        var language = document.getElementById('language-select').value;
        var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="loading-spinner" style="width:14px;height:14px;border-width:2px;"></span> 评测中…';

        var formData = new FormData();
        formData.append('language', language);
        formData.append('code', code);
        formData.append('csrfmiddlewaretoken', csrfToken);
        var contestIdEl = document.getElementById('contest-id');
        if (contestIdEl && contestIdEl.value) {
            formData.append('contest_id', contestIdEl.value);
        }

        fetch(url, { method: 'POST', body: formData })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) {
                var base = (typeof SUBMISSION_DETAIL_BASE !== 'undefined')
                    ? SUBMISSION_DETAIL_BASE
                    : '/submissions/0/';
                window.location.href = base.replace('/0/', '/' + data.submission_id + '/');
            } else {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '▶ 提交评测';
                showToastLocal('提交失败：' + JSON.stringify(data.errors), 'error');
            }
        })
        .catch(function (err) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '▶ 提交评测';
            showToastLocal('网络错误，请重试', 'error');
        });
    });
});


// ==================== 自定义测试面板 ====================
document.addEventListener('DOMContentLoaded', function () {
    var panel = document.getElementById('test-panel');
    var testBtn = document.getElementById('test-btn');
    var useSampleBtn = document.getElementById('use-sample-btn');
    var inputEl = document.getElementById('test-input');
    var outputEl = document.getElementById('test-output');
    var resizer = document.getElementById('test-panel-resizer');

    if (!panel) return;

    // ---------- 使用样例输入 ----------
    if (useSampleBtn) {
        useSampleBtn.addEventListener('click', function () {
            inputEl.value = this.dataset.sample || '';
            inputEl.focus();
        });
    }

    // ---------- 测试运行 ----------
    if (testBtn) {
        testBtn.addEventListener('click', function () {
            runTest();
        });
    }

    // ---------- 拖拽调整高度 ----------
    if (resizer) {
        var startY = 0;
        var startHeight = 0;
        var dragging = false;

        resizer.addEventListener('mousedown', function (e) {
            if (!panel.classList.contains('expanded')) return;
            dragging = true;
            startY = e.clientY;
            startHeight = panel.offsetHeight;
            document.body.classList.add('resizing-test-panel');
            panel.classList.add('resizing');
            e.preventDefault();
        });

        document.addEventListener('mousemove', function (e) {
            if (!dragging) return;
            var deltaY = startY - e.clientY;
            var newHeight = startHeight + deltaY;
            var editorPanel = document.querySelector('.problem-fs-editor');
            var maxHeight = editorPanel ? editorPanel.offsetHeight - 120 : 600;
            var clamped = Math.max(80, Math.min(maxHeight, newHeight));
            panel.style.height = clamped + 'px';
        });

        document.addEventListener('mouseup', function () {
            if (dragging) {
                dragging = false;
                document.body.classList.remove('resizing-test-panel');
                panel.classList.remove('resizing');
            }
        });
    }

    function runTest() {
        var code = window.monacoEditor ? window.monacoEditor.getValue() : '';
        if (!code.trim()) {
            showToastLocal('请先输入代码', 'warning');
            return;
        }

        var language = document.getElementById('language-select').value;
        var testInput = inputEl ? inputEl.value : '';
        var url = testBtn.dataset.url;
        if (!url) return;

        var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')
            ? document.querySelector('[name=csrfmiddlewaretoken]').value
            : getCookieValue('csrftoken');

        testBtn.disabled = true;
        testBtn.innerHTML = '<span class="loading-spinner" style="width:12px;height:12px;border-width:1.5px;display:inline-block;vertical-align:middle;"></span> 运行中';
        outputEl.className = 'test-output';
        outputEl.innerHTML = '<span class="test-output-placeholder">正在编译运行…</span>';

        var formData = new FormData();
        formData.append('code', code);
        formData.append('language', language);
        formData.append('input', testInput);

        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData,
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            testBtn.disabled = false;
            testBtn.innerHTML = '▶ 测试运行';

            if (!data.success) {
                outputEl.className = 'test-output status-error';
                outputEl.textContent = data.error || '测试失败';
                return;
            }
            renderTestOutput(data.result || data);
        })
        .catch(function (err) {
            testBtn.disabled = false;
            testBtn.innerHTML = '▶ 测试运行';
            outputEl.className = 'test-output status-error';
            outputEl.textContent = '网络错误：' + err.message;
        });
    }

    function renderTestOutput(data) {
        var status = data.status || 'AC';
        var output = data.output || '';
        var error = data.error_info || data.error || '';

        var statusClass, bannerClass, bannerText, bodyContent;

        if (status === 'AC' || status === 'ok') {
            statusClass = 'status-ok';
            bannerClass = 'ok';
            bannerText = '✓ 运行成功';
            bodyContent = output || '(无输出)';
        } else if (status === 'TLE' || status === 'timeout') {
            statusClass = 'status-timeout';
            bannerClass = 'timeout';
            bannerText = '⏱ 运行超时';
            bodyContent = error || '代码可能存在死循环';
        } else if (status === 'CE' || status === 'compile_error') {
            statusClass = 'status-error';
            bannerClass = 'err';
            bannerText = '✗ 编译错误';
            bodyContent = error;
        } else if (status === 'RE' || status === 'runtime_error') {
            statusClass = 'status-error';
            bannerClass = 'err';
            bannerText = '✗ 运行时错误';
            bodyContent = error;
        } else if (status === 'WA') {
            statusClass = 'status-error';
            bannerClass = 'err';
            bannerText = '✗ Wrong Answer';
            bodyContent = output || error;
        } else {
            statusClass = 'status-error';
            bannerClass = 'err';
            bannerText = '✗ ' + status;
            bodyContent = error || output || '未知错误';
        }

        outputEl.className = 'test-output ' + statusClass;
        outputEl.innerHTML = '';

        var banner = document.createElement('span');
        banner.className = 'test-status-banner ' + bannerClass;
        banner.textContent = bannerText;
        outputEl.appendChild(banner);

        var body = document.createElement('div');
        body.textContent = bodyContent;
        outputEl.appendChild(body);
    }

    function getCookieValue(name) {
        var v = '; ' + document.cookie;
        var parts = v.split('; ' + name + '=');
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }
});


// ==================== 复制按钮 ====================
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.copy-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var block = this.closest('.sample-block');
            // 获取文本内容时排除按钮本身
            var text = block.childNodes[0].textContent.trim();
            navigator.clipboard.writeText(text).then(function () {
                btn.textContent = '已复制';
                setTimeout(function () { btn.textContent = '复制'; }, 1500);
            });
        });
    });
});


// ==================== Markdown + KaTeX 渲染 ====================
document.addEventListener('DOMContentLoaded', function () {
    if (typeof marked !== 'undefined') {
        marked.setOptions({ gfm: true, breaks: true });
    }

    var sections = [
        { src: 'raw-description',  dst: 'md-description' },
        { src: 'raw-input-desc',   dst: 'md-input-desc' },
        { src: 'raw-output-desc',  dst: 'md-output-desc' },
        { src: 'raw-hint',         dst: 'md-hint' },
    ];

    sections.forEach(function (sec) {
        var scriptEl = document.getElementById(sec.src);
        var targetEl = document.getElementById(sec.dst);
        if (!scriptEl || !targetEl) return;

        var raw = JSON.parse(scriptEl.textContent);
        if (!raw) return;

        // Markdown 渲染
        if (typeof marked !== 'undefined') {
            targetEl.innerHTML = marked.parse(raw);
        } else {
            targetEl.innerHTML = raw.replace(/\n/g, '<br>');
        }

        // KaTeX 渲染
        if (typeof katex !== 'undefined') {
            renderMathInEl(targetEl);
        }
    });
});

function renderMathInEl(el) {
    var html = el.innerHTML;
    // 块级公式 $$...$$
    html = html.replace(/\$\$([\s\S]*?)\$\$/g, function (match, tex) {
        try {
            return katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false });
        } catch (e) { return match; }
    });
    // 行内公式 $...$
    html = html.replace(/(?<!\$)\$(?!\$)((?:[^$\\]|\\.)+?)\$(?!\$)/g, function (match, tex) {
        try {
            return katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false });
        } catch (e) { return match; }
    });
    el.innerHTML = html;
}


// ==================== 工具函数 ====================
function escapeHtmlLocal(str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function showToastLocal(msg, type) {
    if (typeof window.showToast === 'function') {
        window.showToast(msg, type);
    } else {
        alert(msg);
    }
}
