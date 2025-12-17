// arvyn-extension/content.js
// Injects the root widget container and dynamic scripts [cite: 139]

(function() {
    const WIDGET_ID = 'arvyn-omni-widget-root';
    
    // Safety check: Prevent double injection if the script somehow runs twice [cite: 205]
    if (document.getElementById(WIDGET_ID)) {
        console.log('Arvyn Omni-Widget root already present. Injection skipped.');
        return;
    }

    // 1. Create and inject the root container (arvyn-omni-widget-root) [cite: 141, 205]
    const widgetRoot = document.createElement('div');
    widgetRoot.id = WIDGET_ID;
    
    // The fixed positioning is handled by widget.css, ensuring it floats above the native UI [cite: 142, 203]
    document.body.appendChild(widgetRoot);
    
    console.log(`Arvyn Omni-Widget container injected into document.body. [cite: 143]`);

    // 2. Utility to load resources dynamically (JS and CSS) [cite: 143, 205]
    const loadResource = (file, tag) => {
        const element = document.createElement(tag);
        
        if (tag === 'link') {
            // Load CSS [cite: 206]
            element.href = chrome.runtime.getURL(file);
            element.type = 'text/css';
            element.rel = 'stylesheet';
        } else if (tag === 'script') {
            // Load JavaScript [cite: 206]
            element.src = chrome.runtime.getURL(file);
            element.async = false; // Ensure scripts load and execute in order [cite: 143]
        }
        
        // Append to head for scripts and styles [cite: 207]
        document.head.appendChild(element);
        console.log(`Resource loaded: ${file}`);
    };

    // 3. Load necessary CSS and functional JS files dynamically [cite: 143, 205]
    
    // Load styling for the floating widget (widget.css) [cite: 143, 207]
    loadResource('styles/widget.css', 'link'); 
    
    // Load the Socket.IO client library (must be loaded first for the 'io' object) [cite: 207, 213]
    loadResource('lib/socket.io.min.js', 'script'); 
    
    // Load the Socket.IO IPC connection client (socket.js) [cite: 143, 208]
    loadResource('socket.js', 'script'); 
    
    // Load the core UI and Audio Logic (app.js) [cite: 143, 208]
    loadResource('app.js', 'script'); 
    
})();