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
├── .mcp.json.example
├── README.md
├── LICENSE
├── .gitignore
└── docker/
    ├── entrypoint.sh           # /etc/hosts に拒否リストを適用し、uid=1000 に降格
    └── shell-mcp-launch.py     # FastMCP による MCP サーバー本体 (~30 行)
```

- `/etc/hosts` は `docker build` 中は **read-only でバインドマウント** される
  ため、ビルド時に直接書けません。そこで一旦 `/etc/blocked_hosts.list` に
  焼き込み、起動時に `entrypoint.sh` が root で `/etc/hosts` へ追記して
  ロックダウンしたのち、`setpriv` で uid=1000 に降格してから MCP サーバーを
  `exec` します。エージェントが触る shell は常に非root です。
- `shell-mcp-launch.py` は公式 MCP Python SDK の `FastMCP` で書かれた自前の
  サーバーです。許可ディレクトリ・許可シェルを CLI 引数で受け取り
  (`/workspace --shell bash /bin/bash` の形式)、`execute_command` ツールを
  stdio で公開します。タイムアウトは 30 秒固定 (旧 `shell-mcp-server` と同じ)。

