# ER 臨床メモ（静的サイト / GitHub Pages）

Obsidian の `臨床/ER` を同期したリポジトリです。主訴別ページ・疾患詳細・**入院時心電図トリアージ**などを `er-note.css` で整形した HTML として公開します。

## 構成

- `index.html` — トップ（主訴ナビ＋心電図への入口）
- `*.html` / `疾患詳細/**/*.html` — `md_to_html.py` が **同名の `.md` から生成**（手編集しないのが安全）
- `er-note.css` — スタイル
- `md_to_html.py` — Markdown → HTML 変換
- `.nojekyll` — GitHub Pages で Jekyll を無効化

## HTML の生成

### ローカル

```powershell
Set-Location -LiteralPath "<このリポジトリのルート>"
python .\md_to_html.py
```

### GitHub Actions

`main` への push のたびに `.github/workflows/regenerate-html.yml` が `md_to_html.py` を実行し、変更があれば **HTML だけ**を自動コミットします（`.md` は触りません）。

初回に心電図まわりの `.md` だけ push しても、ワークフロー完了後に対応する `.html` がコミットされます。完了後に `git pull` するとローカルと揃います。

## GitHub Pages

1. リポジトリ **Settings → Pages**
2. **Deploy from a branch** — **Branch: `main`**, folder **`/(root)`**

数分後に `https://<user>.github.io/<repo>/` で閲覧できます。

## リモート例

```text
git remote add origin https://github.com/<account>/<repo>.git
git push -u origin main
```

（既に `origin` がある場合は URL だけ合わせてください。）
