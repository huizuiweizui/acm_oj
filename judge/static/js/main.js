/* ============================================
   ACM OJ 全局脚本
   Toast 消息、移动端菜单、Markdown渲染、代码提交
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {

    // ========== 消息自动关闭 ==========
    document.querySelectorAll('.message[data-dismiss]').forEach(function (el) {
        setTimeout(function () { el.classList.add('fade-out'); }, 4000);
        el.querySelector('.message-close')?.addEventListener('click', function () {
            el.classList.add('fade-out');
        });
    });

    // ========== 移动端菜单 ==========
    var toggle = document.getElementById('mobileToggle');
    var navLinks = document.querySelector('.nav-links');
    if (toggle && navLinks) {
        toggle.addEventListener('click', function () {
            navLinks.classList.toggle('open');
            toggle.classList.toggle('active');
        });
    }

    // ========== Markdown 渲染（题面、讨论区） ==========
    document.querySelectorAll('[data-markdown]').forEach(function (el) {
        if (typeof marked !== 'undefined') {
            el.innerHTML = marked.parse(el.textContent);
        }
    });

    // ========== KaTeX 渲染 ==========
    document.querySelectorAll('[data-katex]').forEach(function (el) {
        if (typeof renderMathInElement !== 'undefined') {
            renderMathInElement(el, {
                delimiters: [
                    { left: '$$', right: '$$', display: true },
                    { left: '$', right: '$', display: false },
                    { left: '\\[', right: '\\]', display: true },
                    { left: '\\(', right: '\\)', display: false },
                ],
                throwOnError: false,
            });
        }
    });

    // ========== 涟漪按钮效果（Material Design） ==========
    document.querySelectorAll('.btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            var ripple = document.createElement('span');
            ripple.className = 'ripple';
            var rect = btn.getBoundingClientRect();
            ripple.style.left = (e.clientX - rect.left) + 'px';
            ripple.style.top = (e.clientY - rect.top) + 'px';
            btn.appendChild(ripple);
            setTimeout(function () { ripple.remove(); }, 600);
        });
    });
});


// ========== 代码提交（AJAX） ==========
function submitCode(problemId, csrfToken, contestId) {
    var code = document.getElementById('code-editor')?.value || '';
    var language = document.getElementById('language-select')?.value || 'C++';
    var resultPanel = document.getElementById('result-panel');
    var submitBtn = document.getElementById('submit-btn');

    if (!code.trim()) {
        showToast('请先输入代码', 'warning');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = '评测中...';
    if (resultPanel) {
        resultPanel.innerHTML = '<div class="loading-spinner"></div><span>正在评测，请稍候…</span>';
        resultPanel.className = 'result-panel result-judging';
        resultPanel.style.display = 'flex';
    }

    var formData = new FormData();
    formData.append('language', language);
    formData.append('code', code);
    formData.append('csrfmiddlewaretoken', csrfToken);
    if (contestId) formData.append('contest_id', contestId);

    fetch('/problems/' + problemId + '/submit/', {
        method: 'POST',
        body: formData,
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        submitBtn.disabled = false;
        submitBtn.textContent = '提交代码';

        if (data.success) {
            var st = data.result.status;
            var cls = st === 'AC' ? 'result-ac' : 'result-fail';
            resultPanel.className = 'result-panel ' + cls;
            resultPanel.innerHTML =
                '<div class="result-status">' + st + '</div>' +
                '<div class="result-detail">' +
                (data.result.time_used ? '耗时: ' + data.result.time_used + 'ms' : '') +
                (data.result.error_info ? '<pre class="error-info">' + escapeHtml(data.result.error_info) + '</pre>' : '') +
                '</div>';

            // 刷新提交列表
            if (typeof refreshSubmissions === 'function') refreshSubmissions();
        } else {
            resultPanel.className = 'result-panel result-fail';
            resultPanel.innerHTML = '<div class="result-status">提交失败</div><div class="result-detail">' + JSON.stringify(data.errors) + '</div>';
        }
    })
    .catch(function (err) {
        submitBtn.disabled = false;
        submitBtn.textContent = '提交代码';
        showToast('网络错误，请重试', 'error');
    });
}


// ========== Toast 提示 ==========
function showToast(msg, type) {
    type = type || 'info';
    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = msg;
    document.body.appendChild(toast);
    requestAnimationFrame(function () { toast.classList.add('show'); });
    setTimeout(function () {
        toast.classList.remove('show');
        setTimeout(function () { toast.remove(); }, 300);
    }, 3000);
}


// ========== 工具函数 ==========
function escapeHtml(str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}
