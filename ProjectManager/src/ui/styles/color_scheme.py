class ColorScheme:
    """アプリケーション共通のカラースキーム定義"""
    
    # 基本カラー
    BACKGROUND = '#1A1A1A'      # 濃いグレー（背景）
    CARD_BG = '#2D2D2D'         # やや濃いグレー（カード背景）
    BUTTON_PRIMARY = '#E0E0E0'   # 明るいグレー（プライマリボタン）
    BUTTON_DANGER = '#FF3B30'    # 赤（危険ボタン）
    TEXT_PRIMARY = '#FFFFFF'     # 白（メインテキスト）
    TEXT_SECONDARY = '#B0B0B0'   # グレー（サブテキスト）
    BUTTON_HOVER = '#F5F5F5'     # より明るいグレー（ホバー）
    BUTTON_TEXT = '#1A1A1A'      # 濃いグレー（ボタンテキスト）
    
    # ステータスカラー
    STATUS = {
        '進行中': '#E0E0E0',    # 明るいグレー
        '完了': '#CCCCCC',      # グレー
        '中止': '#999999'       # 暗めのグレー
    }
    
    # 入力フィールド
    INPUT_BG = '#3D3D3D'        # 入力フィールド背景
    INPUT_TEXT = '#FFFFFF'       # 入力フィールドテキスト
    INPUT_BORDER = '#505050'     # 入力フィールドボーダー
    INPUT_PLACEHOLDER = '#808080'  # プレースホルダーテキスト
    
    # フレーム
    FRAME_BORDER = '#404040'     # フレームボーダー
    SEPARATOR = '#404040'        # セパレーター
    
    # バリデーション
    ERROR = '#FF3B30'           # エラー表示
    SUCCESS = '#28A745'         # 成功表示
    
    # スクロールバー
    SCROLLBAR_BG = '#2D2D2D'    # スクロールバー背景
    SCROLLBAR_FG = '#505050'    # スクロールバーフォアグラウンド
    
    # メッセージ
    INFO = '#4A90E2'            # 情報メッセージ
    WARNING = '#FFCC00'         # 警告メッセージ
    
    @classmethod
    def get_hover_color(cls, base_color: str) -> str:
        """ホバー色を生成（ベース色より若干明るく）"""
        return cls.BUTTON_HOVER
    
    @classmethod
    def get_pressed_color(cls, base_color: str) -> str:
        """押下時の色を生成（ベース色より若干暗く）"""
        return '#E0E0E0'  # デフォルトの押下時色