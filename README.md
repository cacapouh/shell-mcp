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
    ├── entrypoint.py           # root で /etc/hosts に拒否リスト追記 → setuid(1000) → exec
    └── shell-mcp-launch.py     # 非 root で動く FastMCP サーバー本体
```

責務を 2 ファイルに分けています。Dockerfile の `ENTRYPOINT` が
`["shell-mcp-entrypoint", "shell-mcp-launch", ...]` と 2 段になっており、
Dockerfile を読むだけで「root で固める → 非 root で serve する」段取りが
分かるようにしてあります。

- **`entrypoint.py`** — コンテナ起動時に root で実行される薄いラッパー。
  `BLOCKED_HOSTS` を `127.0.0.1 <host>` として `/etc/hosts` に追記し、
  `os.setuid(1000)` で mcp ユーザーに降格してから `os.execv` で次のコマンド
  (= `shell-mcp-launch`) に制御を渡します。`/etc/hosts` は `docker build` 中
  read-only でバインドマウントされるためビルド時に直接書けず、起動時に
  root で行うしかない、というのがこの段が存在する理由です。降格しないと
  エージェントが自分で `/etc/hosts` を書き換えてブロックを剥がせてしまい、
  `BLOCKED_HOSTS` 機構が無意味になります。
- **`shell-mcp-launch.py`** — 公式 MCP Python SDK の `FastMCP` で書かれた
  自前のサーバー本体。許可シェルを CLI 引数で受け取り、`execute_command`
  ツールを stdio で公開します。タイムアウトは 30 秒固定。この時点ですでに
  非 root です。

