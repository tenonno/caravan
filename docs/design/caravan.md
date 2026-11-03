# Caravanのロゴ

表示名はCaravan。コピーは「AIと進む、あなたの旅。」。既存の旅人・AIの相棒、青緑・生成り・黄土色の世界観を継続する。

## アセットと容量

`skills/caravan/assets/brand/caravan-logo.png` は透過PNG、640×213px、96,808バイト。画像生成した横長ロゴを、縦横比と透明度を保ってSystem.Drawingの高品質縮小で640px幅にした。元の生成画像は808,365バイトで、配布に含めない。再生成時も完成版を確認し、ロゴ単体を128KiB以内にする。

結果画面・1画面サマリー・開発者詳細・READMEで同じ画像を使う。HTMLには埋め込み、外部通信や画像の別添を必要としない。透過ロゴは生成りの背景に置き、青緑の上へ直接重ねない。画像の比率を固定し、高さはautoにする。

既存の16枚のイラストで場面は十分表現されているため、追加の背景や挿絵は作らない。診断結果・共有JSONにロゴや表示名の変更を保存し直さない。

## 生成方法

組み込み画像生成、透明背景。`assets/journey/SGIC.jpg` をスタイル参照とし、個人の履歴や診断データは入力しない。生成用プロンプト：

```text
Use case: logo-brand. Create ONE finished horizontal logo for a small Japanese AI collaboration reflection tool named exactly 'Caravan'. Input image is STYLE REFERENCE ONLY: keep its friendly travel-storybook spirit, deep teal, warm ochre and muted sage. Do not reproduce the scene. Transparent background, clean edges, no background rectangle, no mockup. Layout: compact distinctive emblem on the left, large legible custom wordmark 'Caravan' on the right. Emblem: a friendly human traveler with a small brimmed hat and a little round AI robot companion walking together, distilled into bold elegant silhouettes with only a few interior details, a short winding trail beneath them. Equal companionship, no hierarchy. Wordmark: warm confident rounded vintage serif lettering, deep teal #21675f, subtly adventurous, exceptionally clear spelling. Restrained handmade print character, very little texture so it compresses well, flat limited colors. Do not add any other text or slogan, no mountains behind the lettering, no badges or frame. Horizontal 3:1 composition with tight balanced margins. Must be recognizable at 240px wide. This is an actual UI header logo, not a poster. Generate only a single lockup.
```


## 16タイプの命名を統一（2026-11-03）

専用のデザイン試作ブランチで、利用者からの命名規則が揃っていないという指摘を受け、「旅の場面での行動＋旅人」に統一した。語尾の相棒・思索家・見届け人・探検家・コレクター・下見びとを混在させない。既存の絵に描かれた物や行動と結びつけ、性格・能力・優劣を名称から推定させない。分析上の違いは短い説明と4軸で示す。名称だけで4軸の全情報を表そうとしない。

名前の正本は `skills/caravan/assets/journey-types.json`。タイプコード・説明・場面・画像・代替テキスト・判定は維持する。生成時の正確な履歴である `skills/ai-sindan-art/references/prompts.json` の旧名称は書き換えない。新しい表示名はADR 0008で定めた表示層の変更に当たり、保存済みの診断内容・日時・共有データを変更しない。

全16名称と絵の対応を確認し、名称・画像・旧分類を扱う既存の3テストおよび結果ページのNode操作テストが成功。架空データによるEdgeの1440px・1280pxで表示・図鑑の操作を確認し、全16タイプの描画を目視した。追加パッケージ・画像生成はない。


## 結果画面の文字階層（2026-11-03）

通常のPC画面は、ページの主題40px・セクション32px・具体例24px・本文／項目ラベル16px・補足13〜14pxを基準にする。役割は `--type-page`、`--type-section`、`--type-item`、`--text-body`、`--type-label`、`--type-meta` で表し、主たる説明はremで拡大できるようにする。既存の明朝はページ／セクションの見出し、ゴシックの700は具体例と項目ラベルに使う。新しいフォントを取得しない。

各表示画面の主題はH1、セクションはH2、具体例はH3、説明項目はH4。タイプ名は分類結果の値として通常テキストで表示し、H1より先にH2を置かない。通常画面から隠れた1枚サマリーは、独立した表示としてH1から始める。見出しを装飾のために重複させない。

具体例の後半は定義リストでラベルと本文を分離する。日本語本文は通常の禁則処理と自然な折り返しを優先し、Latinのch単位で一律に幅を狭めない。短い中央揃えのタイプ説明と見出しはbalance、本文はprettyを補助にする。ID・URL等の長い文字列の折り返しは別扱い。拡大時は隠さず縦に伸ばす。
