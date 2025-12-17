// arvyn-extension/content.js

(function() {
    const WIDGET_ID = 'arvyn-omni-widget-root';
    if (document.getElementById(WIDGET_ID)) {
        return; 
    }

    // 1. Create and inject the root container
    const widgetRoot = document.createElement('div');
    widgetRoot.id = WIDGET_ID;
    document.body.appendChild(widgetRoot);

    // 2. Load CSS
    const link = document.createElement('link');
    link.href = chrome.runtime.getURL('styles/widget.css');
    link.type = 'text/css';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    // 3. Sequential Script Loader (Critical Fix for 'io is not defined')
    function loadScript(fileName) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = chrome.runtime.getURL(fileName);
            script.onload = () => resolve();
            script.onerror = () => reject(`Failed to load ${fileName}`);
            document.head.appendChild(script);
        });
    }

    // Load strict order: Library -> Socket Logic -> App Logic
    loadScript('lib/socket.io.min.js')
        .then(() => loadScript('socket.js'))
        .then(() => loadScript('app.js'))
        .catch(err => console.error("Arvyn Injection Failed:", err));
})();