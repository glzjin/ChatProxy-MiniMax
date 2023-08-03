# ChatProxy-MiniMax
用于将 MiniMax 接口转换为 OpenAI API接口。

接口申请地址：https://api.minimax.chat/

## 使用方法

1. 在自己的机器上用 Docker 进行部署。

```
docker run -p 127.0.0.1:3004:8000 --name minimax-proxy -d glzjin/chatproxy-minimax
```

2. 可以设置反代。（可选）

参考 Caddyfile 内容：

```
minimax-api.*.com {
    tls /etc/caddy/ssl/*.com_server.crt.pem /etc/caddy/ssl/*.com_server.key.pem
    reverse_proxy http://127.0.0.1:3004 {
        header_up Host minimax-api.*.com
    }
}
```

3. 在 (One API)[https://github.com/songquanpeng/one-api] 中进行渠道设置。

![image](https://github.com/glzjin/ChatProxy-MiniMax/assets/7975407/880a3572-184c-4185-a4ca-557f192aa443)

注意密钥由两部分组成，API Key 在前, Group ID 在后，中间竖线分割。

模型说明：

- "abab5-chat": abab5-chat模型
- "abab5.5-chat": abab5.5-chat模型
- "abab5.5-chat-pro": abab5.5-chat，但走 pro 接口调用 [https://api.minimax.chat/document/guides/chat-pro?id=64b79fa3e74cddc5215939f4](https://api.minimax.chat/document/guides/chat-pro?id=64b79fa3e74cddc5215939f4)，可以进行函数调用。

4. 设置倍率。

   ![image](https://github.com/glzjin/ChatProxy-MiniMax/assets/7975407/4d01867b-9505-45ea-903b-c921cd5ae364)

5. Enjoy it.

   ![image](https://github.com/glzjin/ChatProxy-MiniMax/assets/7975407/417c8e47-a7bd-4615-b38f-84637a65381d)

   ![image](https://github.com/glzjin/ChatProxy-MiniMax/assets/7975407/900ef3ea-f03f-445b-aac1-0e4460f64139)

   非流的费用全部记到补全那里了。

## 感谢

- (One API)[https://github.com/songquanpeng/one-api]




