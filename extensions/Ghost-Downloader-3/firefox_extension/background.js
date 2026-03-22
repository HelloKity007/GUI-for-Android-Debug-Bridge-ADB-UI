// background.js

let socket;
let isConnected = false;
let shouldDisableExtension = false;
let heartbeatInterval = null;

// 创建 WebSocket 连接
function connectWebSocket() {
    try {
        socket = new WebSocket("ws://localhost:14370");

        socket.onopen = () => {
            console.log("WebSocket connection opened");
            updateConnectionStatus(true);
            startHeartbeat();
        };

        socket.onmessage = function(event) {
            const message = JSON.parse(event.data);
            // console.log("Received message", message.ClientVersion, message.LatestExtensionVersion);
            if (message.type === "version") {
                // 保存版本信息到 browser.storage.local
                browser.storage.local.set({ ClientVersion: message.ClientVersion }, function() {
                    // console.log("ClientVersion stored:", message.ClientVersion);
                });
                browser.storage.local.set({ LatestExtensionVersion: message.LatestExtensionVersion }, function() {
                    // console.log("LatestExtensionVersion stored:", message.LatestExtensionVersion);
                });
            } else {
                console.log("Received message:", event.data);
            }
        };

        socket.onerror = (error) => {
            console.log("WebSocket error: ", error);
            updateConnectionStatus(false);
            stopHeartbeat(); // 关闭连接时停止心跳
        };

        socket.onclose = () => {
            console.log("WebSocket connection closed, retrying in 2500 microseconds");
            updateConnectionStatus(false);
            if (!shouldDisableExtension) {
                setTimeout(connectWebSocket, 2500);
            }
            stopHeartbeat(); // 关闭连接时停止心跳
        };
    } catch (e) {
        console.log("Exception in WebSocket connection: ", e);
        setTimeout(connectWebSocket, 2500);
    }
}

// 更新连接状态并更新扩展状态和徽章
function updateConnectionStatus(connected) {
    isConnected = connected;
    updateBadge(connected ? "connected" : "disconnected");
    updateStatus(connected);
}

// 更新扩展图标徽章
function updateBadge(status) {
    const badgeColor = (status === "connected") ? "green" : "pink";
    const badgeText = (status === "connected") ? "√" : "×";
    browser.browserAction.setBadgeBackgroundColor({ color: badgeColor });
    browser.browserAction.setBadgeText({ text: badgeText });

}

// 更新扩展状态
function updateStatus(connected) {
    browser.storage.local.set({ isConnected: connected }, () => {
        console.log(`Status updated: ${connected ? "Connected" : "Dis