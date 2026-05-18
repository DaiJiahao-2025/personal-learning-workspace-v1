# LearnFlow B站字幕助手

这是一个最小 Chromium MV3 助手扩展，用来：

1. 读取当前 B 站页面的登录态 cookie
2. 按当前分 P 预抓字幕
3. 把 cookie 与字幕缓存写回本地后端 `http://127.0.0.1:8483`

## 使用方式

1. 在 Chrome / Edge 打开 `chrome://extensions`
2. 开启开发者模式
3. 选择“加载已解压的扩展程序”，指向本目录
4. 先启动 LearnFlow 后端：

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8483 --reload
```

5. 打开一个 B 站视频页，点击扩展图标

徽标含义：

- `OK`：已同步 cookie，且成功预抓字幕
- `CK`：已同步 cookie，但当前视频未抓到字幕
- `OFF`：本地后端没有启动
- `ERR`：同步失败

如果看到 `OFF` 或 `ERR`，把鼠标悬停在扩展图标上可以看到更具体的原因。
