# shell-mcp

[`shell-mcp-server`](https://pypi.org/project/shell-mcp-server/) を Docker
コンテナ化し、指定したホストへの接続を拒否するイメージです。

## カスタムビルド

ビルド時に独自の拒否ホストリストを焼き込めます。

```bash
docker build \
  --build-arg BLOCKED_HOSTS="prod-bastion.example.com,vault.example.com,db.prod.example.com" \
  -t shell-mcp-blocked:custom .
```

デフォルトの `BLOCKED_HOSTS` は `bastion.example.com,vault.example.com` です
ので、必ず自分の環境に合わせて差し替えてください。カンマ区切りで複数指定可、
各エントリ前後の空白はトリムされ、すべて `127.0.0.1` に解決されます。

## MCP クライアント別の設定

### Claude Code

プロジェクト直下に `.mcp.json` を置きます。

```json
{
  "mcpServers": {
    "shell": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "${workspaceFolder}:/workspace",
        "${image}"
      ]
    }
  }
}
```

### VS Code / GitHub Copilot Chat

`.vscode/mcp.json`:

```json
{
  "servers": {
    "shell": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "${workspaceFolder}:/workspace",
        "${image}"
      ]
    }
  }
}
```

## ディレクトリ構成

```
.
├── Dockerfile
├── .mcp.json.example
├── README.md
├── LICENSE
├── .gitignore
└── docker/
    ├── entrypoint.sh           # /etc/hosts に拒否リストを適用し、uid=1000 に降格
    └── shell-mcp-launch.py     # 上流 0.1.0 を asyncio.run() で起動するラッパー
```

`docker/` 配下の 2 ファイルは、いずれも上流側の事情に対処するためのものです。

- `/etc/hosts` は `docker build` 中は **read-only でバインドマウント** される
  ため、ビルド時に直接書けません。そこで一旦 `/etc/blocked_hosts.list` に
  焼き込み、起動時に `entrypoint.sh` が root で `/etc/hosts` へ追記して
  ロックダウンしたのち、`setpriv` で uid=1000 に降格してから MCP サーバーを
  `exec` します。エージェントが触る shell は常に非root です。
- `shell-mcp-server==0.1.0` (執筆時点で PyPI 唯一のバージョン) は、
  console-script が `sys.exit(main())` を呼び出すのに対して `main` が
  `async` 関数なので、コルーチンが await されないままプロセスが終了して
  しまいます。`shell-mcp-launch.py` はその `main` を `asyncio.run` で
  起動するだけの 5 行のラッパーです。**上流パッケージ本体には手を入れて
  いません。**

