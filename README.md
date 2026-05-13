# shell-mcp

公式 MCP Python SDK (`mcp` パッケージ) の **FastMCP** で実装した最小構成の
シェル実行 MCP サーバーを Docker コンテナ化し、指定したホストへの接続を
拒否するイメージです。公開している MCP ツールは `execute_command(command,
shell, cwd)` の 1 つだけです。

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
├── README.md
├── LICENSE
├── .gitignore
└── docker/
    └── shell-mcp-launch.py     # /etc/hosts ロックダウン + 権限降格 + FastMCP サーバー
```

`shell-mcp-launch.py` は公式 MCP Python SDK の `FastMCP` で書かれた自前の
サーバーです。コンテナ起動時に root で実行され、

1. `BLOCKED_HOSTS` 環境変数を `127.0.0.1 <host>` として `/etc/hosts` に追記し、
   `/etc/hosts` の所有権/パーミッションをロックダウン
2. `os.setuid(1000)` (mcp ユーザー) に降格
3. 許可ディレクトリ/許可シェルを CLI 引数 (`/workspace --shell bash /bin/bash`)
   で受け取り、`execute_command` ツールを stdio で公開

の順で動きます。`/etc/hosts` は `docker build` 中 read-only でバインド
マウントされるためビルド時に直接書けず、この起動時ステップが必要です。
エージェントが触る shell は常に非 root、タイムアウトは 30 秒固定です。

