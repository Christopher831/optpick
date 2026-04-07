const TRANSLATIONS = {
  en: {
    "site-title": "An Optimal Samples Selection System",
    "nav-home": "Home",
    "nav-database": "Database",
    "form-title": "Please input the following parameters",
    "mode-title": "Sample Selection Mode",
    "mode-random": "Random n samples",
    "mode-manual": "Input n samples manually",
    "manual-label": "Enter n numbers, comma-separated:",
    "btn-execute": "Execute",
    "btn-clear": "Clear",
    "btn-store": "Store to Database",
    "btn-back": "Back",
    "btn-print": "Print",
    "btn-display": "Display",
    "btn-delete": "Delete",
    "btn-cancel": "Cancel",
    "results-title": "Results",
    "selected-samples": "Selected {n} samples",
    "optimal-groups": "{num} optimal groups of {k}",
    "th-index": "#",
    "th-group-members": "Group members",
    "db-title": "Database Resources",
    "th-label": "Label",
    "th-params": "Parameters",
    "th-groups": "Groups",
    "th-created": "Created",
    "th-actions": "Actions",
    "delete-confirm": "Delete this record?",
    "empty-msg": "No records yet. Go to <a href=\"/app\">Home</a> to run the algorithm and store results.",
    "footer-system": "Optimal Samples Selection System",
    "footer-dev": "Developed by Wei Chong, Xiao Rui, Sun Haoran",
    "login-title": "Welcome",
    "login-subtitle": "Sign in to save and manage your results",
    "login-or": "or",
    "btn-google-login": "Sign in with Google",
    "btn-guest": "Continue as Guest",
    "guest-note": "Guests can use the algorithm but cannot save results.",
    "btn-logout": "Logout",
    "btn-signin": "Sign in",
    "guest-label": "Guest",
    "login-required": "Please log in to save results.",
    "elapsed-time": "Elapsed: {ms}ms",
    "timeout-warning": "Algorithm timed out, returning current best solution.",
    "new-best": "New best!",
    "tied-best": "Tied with best ({best})",
    "vs-best": "Best: {best}"
  },
  zh: {
    "site-title": "最优样本选择系统",
    "nav-home": "首页",
    "nav-database": "数据库",
    "form-title": "请输入以下参数",
    "mode-title": "样本选择方式",
    "mode-random": "随机选择 n 个样本",
    "mode-manual": "手动输入 n 个样本",
    "manual-label": "请输入 n 个数字，用逗号分隔：",
    "btn-execute": "执行",
    "btn-clear": "清除",
    "btn-store": "保存到数据库",
    "btn-back": "返回",
    "btn-print": "打印",
    "btn-display": "查看",
    "btn-delete": "删除",
    "btn-cancel": "取消",
    "results-title": "计算结果",
    "selected-samples": "已选择 {n} 个样本",
    "optimal-groups": "{num} 个最优分组（每组 {k} 个）",
    "th-index": "#",
    "th-group-members": "分组成员",
    "th-label": "标签",
    "th-params": "参数",
    "th-groups": "分组数",
    "th-created": "创建时间",
    "th-actions": "操作",
    "delete-confirm": "确定删除此记录？",
    "empty-msg": "暂无记录。前往<a href=\"/app\">首页</a>运行算法并保存结果。",
    "db-title": "数据库记录",
    "footer-system": "最优样本选择系统",
    "footer-dev": "开发者：韦翀、肖瑞、孙浩然",
    "login-title": "欢迎",
    "login-subtitle": "登录以保存和管理您的结果",
    "login-or": "或",
    "btn-google-login": "使用 Google 登录",
    "btn-guest": "以访客身份继续",
    "guest-note": "访客可以使用算法，但无法保存结果。",
    "btn-logout": "退出登录",
    "btn-signin": "登录",
    "guest-label": "访客",
    "login-required": "请登录后保存结果。",
    "elapsed-time": "耗时：{ms}ms",
    "timeout-warning": "算法超时，返回当前最优解。",
    "new-best": "新纪录！",
    "tied-best": "与最优持平（{best}）",
    "vs-best": "历史最优：{best}"
  }
};

function setLang(lang) {
  localStorage.setItem("lang", lang);
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    const tmpl = TRANSLATIONS[lang][key];
    if (!tmpl) return;
    let text = tmpl;
    if (el.dataset.i18nN) text = text.replace("{n}", el.dataset.i18nN);
    if (el.dataset.i18nNum) text = text.replace("{num}", el.dataset.i18nNum);
    if (el.dataset.i18nK) text = text.replace("{k}", el.dataset.i18nK);
    if (el.dataset.i18nMs) text = text.replace("{ms}", el.dataset.i18nMs);
    if (el.dataset.i18nBest) text = text.replace("{best}", el.dataset.i18nBest);
    if (text.includes("<a ")) {
      el.innerHTML = text;
    } else {
      el.textContent = text;
    }
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (TRANSLATIONS[lang][key]) el.placeholder = TRANSLATIONS[lang][key];
  });
  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });
}

document.addEventListener("DOMContentLoaded", function() {
  const lang = localStorage.getItem("lang") || "en";
  setLang(lang);
});
