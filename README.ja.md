# Peneo

[English README](README.md)

Peneo は、ターミナルで作業しつつ GUI アプリとも自然につなげたい環境向けの、Textual ベースの TUI ファイルマネージャです。  
キーバインドを覚え込むことを前提にしたツールではなく、GUI のファイラーに近い感覚で主要操作へたどり着けることを重視しており、よく使う操作は画面上のヘルプに常時表示されるため迷いにくくしています。

![Peneo screenshot](docs/resources/screen1.png)

_現在の 3 ペイン UI。親ディレクトリ、現在のディレクトリ、子ディレクトリを並べ、混在するプロジェクトファイルも見える状態です。_

## 特徴

- 親 / 現在 / 子ディレクトリを並べた 3 ペイン表示で、周辺の階層コンテキストを保ちやすい
- ブラウザ 3 ペインの下に、現在ディレクトリ起点の埋め込み split terminal を単一ショートカットで開閉できる
- よく使う操作は画面上のヘルプに常時表示し、使用頻度の低い操作はコマンドパレットにまとめる構成
- ディレクトリ移動、複数選択、コピー、カット、貼り付け、ゴミ箱削除、リネーム、新規作成をキーボードだけで操作
- フィルタ入力、コマンドパレットからの再帰ファイル検索、config 編集、ソート切り替え、隠しファイル表示切り替えをサポート
- ファイルは OS の既定アプリで開き、現在ディレクトリは OS のファイルマネージャやターミナルへつなげられ、必要なら `e` で現在のターミナル内エディタも起動できる
- `peneo-cd` を使った任意の shell 連携で、終了後に最後のディレクトリへ戻れる
- 削除はゴミ箱経由で、貼り付け競合時は overwrite / skip / rename を選べる

## スクリーンショット

先頭画像は基本の 3 ペイン画面です。以下では、アプリの主要ワークフローを順に示します。

### Split Terminal

![Peneo split terminal screenshot](docs/resources/screen-split-terminal.png)

_`Ctrl+T` で埋め込み split terminal を開き、上段のブラウザ 3 ペインを保ったまま下段のシェル出力を確認している状態です。_

### 複数選択と貼り付け競合

![Peneo multi-select screenshot](docs/resources/screen-multi-select.png)

_`Space` で複数ファイルを選択し、そのまま copy/paste の競合ダイアログを表示した状態です。_

### コマンドパレット

![Peneo command palette screenshot](docs/resources/screen-command-palette.png)

_`:` でコマンドパレットを開き、ブラウザ画面を離れずに主要コマンドへアクセスしている状態です。_

### フィルタ入力

![Peneo filter screenshot](docs/resources/screen-filter.png)

_`/` でフィルタ入力を開き、現在ディレクトリの内容をその場で絞り込んでいる状態です。_

### 属性ダイアログ

![Peneo attributes screenshot](docs/resources/screen-attributes.png)

_読み取り専用の属性ダイアログで、パス、サイズ、更新日時、権限などを確認している状態です。_

## 現在できること

- ディレクトリの閲覧と移動
- ファイル / ディレクトリの複数選択
- copy / cut / paste
- ゴミ箱への削除
- 単一対象のリネーム
- 新規ファイル / 新規ディレクトリ作成
- ファイル名フィルタ
- コマンドパレットからの再帰ファイル検索
- コマンドパレットからの config 編集と `config.toml` への保存
- 名前 / 更新日時 / サイズでのソート切り替え
- ディレクトリ優先表示の ON / OFF
- パスのクリップボードコピー
- 現在ディレクトリを OS のファイルマネージャで開く
- 現在ディレクトリでのターミナル起動
- 現在ディレクトリ起点の埋め込み split terminal を開く
- 隠しファイル表示切り替え
- ファイルの既定アプリ起動
- ファイルの現在のターミナル内エディタ起動
- `config.toml` による表示設定・挙動設定・ターミナル起動設定の永続化
- 任意の shell 連携による終了後のディレクトリ引き継ぎ

## インストール

`uv` が入っている環境で、リポジトリを clone してからツールとしてインストールします。

```bash
git clone https://github.com/devgamesan/peneo.git
cd peneo
uv tool install --from . peneo
```

更新時は最新を pull したあとに同じコマンドを再実行してください。

## 起動

```bash
peneo
```

開発中にローカル checkout から直接起動したい場合は、リポジトリ直下で次を使えます。

```bash
uv run peneo
```

`peneo` 本体は親シェルのカレントディレクトリを直接変更できません。終了時に Peneo で最後に開いていたディレクトリへシェル側も移動したい場合は、まず次の 1 行を `.bashrc` や `.zshrc` に追加してください。

```bash
eval "$(peneo init bash)"  # bash の場合
eval "$(peneo init zsh)"   # zsh の場合
```

新しいシェルを開くか、現在のシェルでも同じ行を 1 回実行するとすぐ有効になります。これで `peneo-cd` というシェル関数が定義されます。以後、その挙動が必要なときだけ通常の `peneo` の代わりに次を使います。

```bash
peneo-cd
```

この挙動が不要なら、通常どおり `peneo` / `uv run peneo` を使えます。

ファイルにカーソルを合わせた状態で `e` を押すと、現在のターミナル上で `$EDITOR`、`nvim`、`vim`、`nano` などのターミナルエディタへ切り替えられます。

## 設定ファイル

Peneo は起動時にユーザー設定用の `config.toml` を読み込みます。ファイルがまだ存在しない場合は、既定値入りの設定ファイルを自動生成します。

- Linux: `${XDG_CONFIG_HOME:-~/.config}/peneo/config.toml`
- macOS: `~/Library/Application Support/peneo/config.toml`
- Windows 向けの設定パスも予約していますが、Windows ネイティブ実行自体は引き続き非対応です

設定できる項目は次のとおりです。

| セクション | キー | 値 | 説明 |
| --- | --- | --- | --- |
| `terminal` | `linux` | shell 形式コマンド文字列の配列 | Linux 向けの任意ターミナル起動コマンドです。作業ディレクトリは `{path}` で埋め込みます。空文字や不正なエントリは無視されます。 |
| `terminal` | `macos` | shell 形式コマンド文字列の配列 | macOS 向けの任意ターミナル起動コマンドです。検証ルールは Linux と同じです。 |
| `terminal` | `windows` | shell 形式コマンド文字列の配列 | Windows / WSL ブリッジ向けの任意ターミナル起動コマンドです。Windows ネイティブ実行は未対応ですが設定キー自体は受け付けます。 |
| `display` | `show_hidden_files` | `true` / `false` | 起動時の隠しファイル表示状態です。 |
| `display` | `default_sort_field` | `name` / `modified` / `size` | 中央ペインの初期ソート項目です。 |
| `display` | `default_sort_descending` | `true` / `false` | `true` のとき、起動時のソートを降順にします。 |
| `display` | `directories_first` | `true` / `false` | 中央ペインでディレクトリをファイルより先にまとめて表示します。 |
| `behavior` | `confirm_delete` | `true` / `false` | ゴミ箱削除の前に確認ダイアログを表示します。 |
| `behavior` | `paste_conflict_action` | `prompt` / `overwrite` / `skip` / `rename` | 貼り付け競合時の既定動作です。`prompt` の場合は競合ダイアログを維持します。 |

例:

```toml
[terminal]
linux = ["konsole --working-directory {path}", "gnome-terminal --working-directory={path}"]
macos = ["open -a Terminal {path}"]
windows = ["wt -d {path}"]

[display]
show_hidden_files = false
default_sort_field = "name"
default_sort_descending = false
directories_first = true

[behavior]
confirm_delete = true
paste_conflict_action = "prompt"
```

設定値が不正でも起動は止めず、該当項目だけ既定値へフォールバックして初回ロード後に警告を表示します。

## 基本操作

主要キーは次のとおりです。

| 状態 | キー | 動作 |
| --- | --- | --- |
| 通常時 | `↑` / `k` | カーソル移動 |
| 通常時 | `↓` / `j` | カーソル移動 |
| 通常時 | `←` / `h` / `Backspace` | 親ディレクトリへ移動 |
| 通常時 | `→` / `l` | ディレクトリなら入る |
| 通常時 | `Enter` | ディレクトリなら入る、ファイルなら既定アプリで開く |
| 通常時 | `e` | カーソル中のファイルを `$EDITOR`、`nvim`、`vim`、`nano` などのターミナルエディタで開く |
| 通常時 | `F5` | 現在ディレクトリを再読み込み |
| 通常時 | `Space` | 選択トグル後に次行へ移動 |
| 通常時 | `y` | 選択中の項目、またはカーソル項目をコピー対象にする |
| 通常時 | `x` | 選択中の項目、またはカーソル項目をカット対象にする |
| 通常時 | `p` | 現在ディレクトリへ貼り付け |
| 通常時 | `Delete` | 選択中の項目、またはカーソル項目をゴミ箱へ移動（既定では確認あり、設定で変更可能） |
| 通常時 | `F2` | 単一対象のリネーム入力を開始 |
| 通常時 | `/` | フィルタ入力を開始 |
| 通常時 | `s` | ソート順を循環切り替え |
| 通常時 | `d` | ディレクトリ優先表示を切り替え |
| 通常時 | `q` | アプリを終了 |
| 通常時 | `Esc` | フィルタ有効時はフィルタ解除、そうでなければ選択解除 |
| 通常時 | `:` | コマンドパレットを開く |
| 通常時 | `Ctrl+T` | 埋め込み split terminal を開閉する |
| 通常時（split terminal 表示中） | 文字入力やブラウザ操作キー | split terminal が入力を持つ間は無効 |
| フィルタ入力中 | 文字入力 | フィルタ文字列を更新 |
| フィルタ入力中 | `Backspace` | 1 文字削除 |
| フィルタ入力中 | `Enter` / `↓` | フィルタを適用して一覧操作へ戻る |
| フィルタ入力中 | `Esc` | フィルタを解除する |
| コマンドパレット表示中 | 文字入力 / `↑` / `↓` / `k` / `j` / `Enter` / `Esc` | コマンドを絞り込み、選択、実行、キャンセル |
| split terminal フォーカス中 | 文字入力 / 矢印 / `Enter` / `Backspace` / `Esc` / `Tab` | 入力を埋め込みシェルへ送る |
| split terminal フォーカス中 | `Ctrl+T` | 埋め込み split terminal を閉じる |
| 名前入力中 | 文字入力 / `Backspace` / `Enter` / `Esc` | リネームや新規作成の入力値を編集、確定、キャンセル |
| 確認ダイアログ表示中 | `Enter` / `Esc` | 削除確認を確定 / 中止 |
| 確認ダイアログ表示中 | `o` / `s` / `r` / `Esc` | 貼り付け競合を overwrite / skip / rename / cancel |

`e` は GUI アプリを別ウィンドウで開くのではなく、現在のターミナルセッション内でターミナルエディタへ切り替える操作です。

## コマンドパレット

使用頻度の低い操作は `:` で開くコマンドパレットにまとめています。現在使える主なコマンドは次のとおりです。

| コマンド | 表示条件 | 動作 / 補足 |
| --- | --- | --- |
| `Find file` | 常に表示 | コマンドパレットを再帰ファイル検索モードへ切り替えます。現在ディレクトリ配下をファイル名の大文字小文字を無視した部分一致で検索し、隠しファイル表示が無効な間は hidden path を除外します。`Enter` で親ディレクトリを開き、そのファイルへカーソルを移します。 |
| `Show attributes` | 単一対象が選択中またはフォーカス中のとき | `Name`、`Type`、`Path`、`Size`、`Modified`、`Hidden`、`Permissions` を表示する読み取り専用ダイアログを開きます。 |
| `Copy path` | 対象が 1 件以上あるとき | 選択中のパス一覧、または未選択時はフォーカス中のパスをシステムクリップボードへコピーします。 |
| `Open in file manager` | 常に表示 | 現在ディレクトリを OS のファイルマネージャで開きます。 |
| `Open terminal here` | 常に表示 | `config.toml` の設定を優先しつつ、現在ディレクトリ起点で外部ターミナルを起動します。 |
| `Open split terminal` / `Close split terminal` | 常に表示 | 埋め込み split terminal を開閉します。ラベルは表示状態に応じて切り替わり、開いた後の作業ディレクトリはブラウザ側の移動に自動追従しません。 |
| `Show hidden files` / `Hide hidden files` | 常に表示 | ブラウザ 3 ペインの隠しファイル表示を切り替えます。ラベルは現在状態を反映します。 |
| `Edit config` | 常に表示 | 起動時設定を編集する overlay を開きます。`↑` / `↓` で項目移動、`←` / `→` / `Enter` で値変更、`s` で `config.toml` 保存、`e` で生の設定ファイルをターミナルエディタで開けます。 |
| `Create file` | 常に表示 | 現在ディレクトリで新規ファイル作成の入力を開始します。 |
| `Create directory` | 常に表示 | 現在ディレクトリで新規ディレクトリ作成の入力を開始します。 |

## 対応環境と注意

- 現時点で動作確認している OS は Ubuntu のみです。
- 既定アプリ起動、ファイルマネージャ起動、ターミナル起動などの GUI 連携も主にその環境で確認しています。
- 埋め込み split terminal は現状 POSIX 環境、特に Ubuntu/Linux と WSL を前提にしています。
- 外部起動まわりは Linux、macOS、WSL を意識したフォールバックを持ちます。Windows ネイティブ実行はサポート対象外です。
- `config.toml` でターミナル起動コマンドを指定した場合は、その設定を組み込みフォールバックより優先します。
- WSL では `wslview`、`explorer.exe`、`clip.exe` のような Windows 側ブリッジを優先し、WSLg や Linux デスクトップ向けのフォールバックも維持します。
- まだ開発途中です。挙動やキーバインドは今後見直す可能性があります。
- ファイル操作は、選択したディレクトリエントリ自体に対して行われます。選択中の項目が symlink の場合も、リンク先を暗黙に辿って変更せず、symlink エントリ自体を操作します。

## 関連ドキュメント

- 実装構造: [docs/architecture.md](docs/architecture.md)
- MVP メモ: [docs/spec_mvp.md](docs/spec_mvp.md)
- 性能確認メモ: [docs/performance.md](docs/performance.md)

## 開発者向け

開発環境を作る場合は次を実行します。

```bash
uv sync --python 3.12 --dev
```

テストと静的検査:

```bash
uv run ruff check .
uv run pytest
```

README 用スクリーンショットの再生成:

```bash
uv run python scripts/generate_readme_screenshots.py
```
