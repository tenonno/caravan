# 少人数に渡すための公開配布

アクセス権を個別に付与せず試してもらうため、MITライセンスの公開GitHubリポジトリを使う。大規模なサービス運用や、履歴を集めるサーバーは設けない。

## 公開するもの

`distribution-files.txt` に1行1ファイルで列挙したソース・文書・テスト・画像だけ。診断スキルは全アセットを含める。追加ファイルは自動では配布されないため、内容を確認して一覧も更新する。

```text
python -m unittest discover -s tests -v
python scripts/build_release.py
```

出力は `output/distribution/caravan.zip` と `SHA256SUMS`。ZIPは毎回上書きし、中身は `caravan/` フォルダにまとめる。Gitはビルド時の依存にしない。同じファイルからは同じZIPを生成する。

一覧は秘密情報の自動検出機能ではない。公開前には一覧に載ったファイルの本文・画像も点検する。既に公開したファイルに後から私的情報を書かない。

## 初回のGitHub公開

1. ZIPを新しい空の場所に展開する。元の開発フォルダや `.git` はコピーしない。
2. 展開先の内容を確認し、新しいGitリポジトリとして初期コミットを作る。
3. 公開先のアカウントとリポジトリ名を確認して、その新しい履歴だけをpushする。
4. 配布する相手にはリポジトリのURLとREADMEの依頼文を渡す。ReleaseへZIPを添付してもよい。

開発用Gitの履歴は公開に使わない。現在のファイルを削除しても過去のコミットは消えないため、公開には明示一覧から作る新しい履歴だけを使う。個人の発表資料は開発用を含むリポジトリの外で管理し、追跡しない。公開先はこの文書に個人アカウントを固定せず管理する。

## 更新

開発リポジトリの `origin` を公開GitHubに設定し、`public/main` で `origin/main` を追跡する。公開用の作業場所は同じリポジトリのworktree `output/publish-main/` とする。別のGitリポジトリにだけremoteを設定する運用は使わない。

更新は次の順に行う。

1. `git fetch origin` で公開先を確認し、公開用worktreeを `origin/main` までfast-forwardする。競合や公開先だけの変更があれば先に照合する。
2. テストと `python scripts/build_release.py` を実行する。新しい公開文書も `distribution-files.txt` に明示する。
3. 公開用worktreeの追跡ファイルを明示一覧と一致させる。一覧外の削除対象も確認する。ZIPの `caravan/` 以下だけを反映し、開発用の `.git` や私的な出力をコピーしない。
4. 公開用worktreeで差分・テスト・公開対象を確認してコミットする。
5. 公開を依頼された場合だけ、開発リポジトリから `git push origin public/main:main` を実行する。
6. 公開先のコミットIDと、公開用ブランチのIDが一致することを確認する。

`push.default=nothing` とし、引数なしのpushは無効にする。開発ブランチを `main` にmergeしたり、`--all`・`--mirror`・force pushで送ったりしない。公開用ブランチは既存の公開履歴に続け、明示一覧以外の内容と開発履歴を含めない。既存の診断出力も公開用worktreeへ移さない。背景は [ADR 0030](adr/0030-explicit-publication-remote.md) を参照。

利用者にはREADMEのスキル導入手順を渡す。CodexはSkill InstallerへスキルのGitHub URLを指定し、Claude Codeは個人用スキルの配置場所へフォルダ一式を取得する。導入後は名前で呼び出す。ZIPは公開用ソースの切り出し・補助的な配布に使い、利用者の手動展開を必須にしない。

インストール時は履歴を読まない。スキルフォルダにはコード・定義・画像・ライセンスだけを置き、私的な出力は診断の作業フォルダへ分離する。詳細は [ADR 0012](adr/0012-installed-skill-workspace.md)。

READMEの手順は利用者自身のPCで履歴を扱う。本人の結果を集める場合は、本人が選んだ共有JSONや画像を別途受け取る。Issueへ履歴・抜粋・レポートを添付するよう案内しない。
