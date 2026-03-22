# Plain アーキテクチャ概要

このドキュメントは、現在の `Plain` の実装構造を俯瞰するためのものです。  
MVP 仕様全体ではなく、`2026-03-22` 時点でコード上に存在する責務分割とデータフローを対象にします。

## 1. 目的

現在の実装は、以下を明確に分離する方針で組まれています。

- `UI`: 表示と Textual イベント受け取り
- `input dispatcher`: キー入力を `Action` に正規化
- `reducer`: `AppState` を純粋関数で更新
- `selectors`: `AppState` を表示用モデルへ変換
- `models`: 表示モデルと状態モデル
- `services/adapters`: 将来の副作用や OS 依存処理の受け皿

## 2. 全体構成

```mermaid
flowchart LR
    subgraph UI["UI layer (`src/plain/ui`, `src/plain/app.py`)"]
        App["PlainApp"]
        Pane["MainPane / SidePane"]
        Status["StatusBar"]
    end

    subgraph State["State layer (`src/plain/state`)"]
        Input["input.py\nキー入力 dispatcher"]
        Actions["actions.py\nAction 定義"]
        Reducer["reducer.py\nreduce_app_state"]
        Selectors["selectors.py\nselect_shell_data"]
        Models["models.py\nAppState / PaneState / UiMode"]
    end

    subgraph Domain["Display models (`src/plain/models`)"]
        Shell["shell_data.py\nThreePaneShellData / StatusBarState"]
    end

    subgraph Future["Future side effects"]
        Services["services/"]
        Adapters["adapters/"]
    end

    App --> Input
    Input --> Actions
    App --> Reducer
    Reducer --> Models
    App --> Selectors
    Selectors --> Models
    Selectors --> Shell
    Shell --> Pane
    Shell --> Status
    Reducer -. extension .-> Services
    Services -. OS/FS boundary .-> Adapters
```

## 3. キー入力から描画までの流れ

現在の中核フローは「入力 -> Action -> 状態更新 -> Selector -> 再描画」です。

```mermaid
sequenceDiagram
    participant User as User
    participant App as PlainApp
    participant Input as dispatch_key_input
    participant Reducer as reduce_app_state
    participant Selector as select_shell_data
    participant UI as Pane/StatusBar

    User->>App: キー入力
    App->>Input: ui_mode, key, character
    Input-->>App: Action の列 or warning message
    loop 各 Action
        App->>Reducer: AppState, Action
        Reducer-->>App: next AppState
    end
    App->>Selector: 最新 AppState
    Selector-->>App: ThreePaneShellData
    App->>UI: body / status-bar を再描画
```

## 4. ディレクトリ責務

### `src/plain/app.py`

- `PlainApp` がアプリ全体の組み立て役
- Textual の `Key` イベントを受ける
- `dispatch_key_input()` と `reduce_app_state()` を呼ぶ
- selector の結果を使って UI を再描画する

### `src/plain/ui/`

- `MainPane`, `SidePane`, `StatusBar` は表示責務に限定
- widget 自体はキー意味の分岐を持たない
- 現在の入力解釈は app / state 側で一元管理する

### `src/plain/state/actions.py`

- reducer が受け取る入力単位を定義する
- 現在は次のような Action がある
  - UI モード変更
  - カーソル移動
  - 選択トグル
  - フィルタ開始 / 確定 / 取消し
  - ステータスメッセージ更新

### `src/plain/state/input.py`

- `ui_mode` ごとに同じキーの意味を切り替える
- `BROWSING`, `FILTER`, `CONFIRM`, `BUSY` の入力を現在サポート
- 未サポート入力は warning message に変換する

### `src/plain/state/reducer.py`

- `AppState` を純粋関数で更新し、`ReduceResult(state, effects)` を返す
- effect は純粋な記述として返し、実行自体は app / services 側に委ねる
- browser snapshot の request / success / failure を action として state に戻す

### `src/plain/state/selectors.py`

- `AppState` を UI 用の `ThreePaneShellData` に変換する
- フィルタとソートをここで適用する
- ステータスバー表示文字列の元データもここで組み立てる

### `src/plain/models/`

- `shell_data.py` は描画専用モデル
- `state/models.py` は reducer 管理対象のアプリ状態と notification / snapshot 契約を持つ

### `src/plain/services/`

- `BrowserSnapshotLoader` で非同期読み込み境界を切る
- 現在は `FakeBrowserSnapshotLoader` が delay / failure を含むテスト用ロードを担う
- 実ファイルシステム実装は後続 Issue で差し替える

## 5. 現在のモードと入力境界

```mermaid
stateDiagram-v2
    [*] --> BROWSING
    BROWSING --> FILTER: Ctrl+F
    FILTER --> BROWSING: Enter
    FILTER --> BROWSING: Esc
    CONFIRM --> BROWSING: Esc / Enter
    RENAME --> BROWSING: Esc
    CREATE --> BROWSING: Esc

    BUSY --> BUSY: 任意キーは無視
```

補足:

- `BROWSING`
  - `Up`, `Down`, `Space`, `Esc`, `Ctrl+F` を処理
- `FILTER`
  - 文字入力、`Backspace`, `Space`, `Enter`, `Esc` を処理
- `CONFIRM`, `BUSY`
  - 土台だけあり、通常フローからはまだ本格利用していない
- `RENAME`, `CREATE`
  - 型と退避先はあるが、まだ本実装前

## 6. 現在できること / まだできないこと

### できること

- ダミー `AppState` をもとに 3 ペイン UI を起動
- 可視行のカーソル移動
- 選択トグルと全解除
- フィルタ入力と再帰フラグ切り替え
- モード別キー解釈
- Textual worker を使った非同期 effect 実行
- 古い browser snapshot 結果の破棄
- ステータスバーへの warning / error 通知表示

### まだできないこと

- 実ファイルシステムの読み込み
- 実ディレクトリ移動
- ファイル open / copy / cut / paste / rename / delete / create
- 履歴移動や sort 切り替えの UI 操作
- popup ベースの通知 UI

## 7. 今後の拡張ポイント

将来の実装は、基本的に次の順で差し込む想定です。

```mermaid
flowchart TD
    Key["新しいキー操作"] --> Input["input.py に dispatch 追加"]
    Input --> Action["Action 追加"]
    Action --> Reducer["reducer に状態遷移追加"]
    Reducer --> Effect["ReduceResult.effects に effect 追加"]
    Reducer --> Selector["必要なら selector 更新"]
    Effect --> Service["app が Textual worker 経由で services を実行"]
    Service --> Adapter["OS/FS 操作は adapters へ委譲"]
    Service --> ActionBack["完了時は action に戻す"]
    ActionBack --> Reducer
    Selector --> UI["UI は表示更新だけ行う"]
```

この流れを守ることで、widget ごとの分岐追加を避けつつ、操作の追加を局所化できます。
