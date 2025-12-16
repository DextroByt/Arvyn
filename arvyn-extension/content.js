// arvyn-extension/content.js

// Injects the root widget container and dynamic scripts 
(function() {
    const WIDGET_ID = 'arvyn-omni-widget-root';
    if (document.getElementById(WIDGET_ID)) {
        return; 
    }

    // 1. Create and inject the root container
    const widgetRoot = document.createElement('div');
    widgetRoot.id = WIDGET_ID;
    document.body.appendChild(widgetRoot);

    // 2. Load necessary CSS and functional JS files dynamically
    const loadResource = (file, tag) => {
        const element = document.createElement(tag);
        if (tag === 'link') {
            element.href = chrome.runtime.getURL(file);
            element.type = 'text/css';
            element.rel = 'stylesheet';
        } else if (tag === 'script') {
            element.src = chrome.runtime.getURL(file);
        }
        document.head.appendChild(element);
    };

    loadResource('styles/widget.css', 'link');
    // Assuming Socket.IO client library is bundled/local (lib/socket.io.min.js)
    loadResource('lib/socket.io.min.js', 'script');
    loadResource('socket.js', 'script'); 
    loadResource('app.js', 'script'); 
})();


