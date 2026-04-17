# ER Vertigo Static Site

このフォルダは `めまい.html` を静的公開するための最小構成です。

## 公開ファイル

- `index.html` (トップURL用エントリ)
- `めまい.html` (本体)
- `er-note.css` (スタイル)
- `.nojekyll` (GitHub Pagesで静的配信を優先)

## GitHub Pages 公開手順

1. このフォルダで初期化
   - `git init`
   - `git add .`
   - `git commit -m "Initialize static site for ER vertigo page"`
2. mainブランチを使用
   - `git branch -M main`
3. GitHubで空のリポジトリを作成して接続
   - `git remote add origin https://github.com/<your-account>/<repo>.git`
4. push
   - `git push -u origin main`
5. GitHubの `Settings > Pages` で
   - Source: `Deploy from a branch`
   - Branch: `main` / `/(root)`

数分後に `https://<your-account>.github.io/<repo>/` で閲覧できます。
