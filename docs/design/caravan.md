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
