import bpy

# ブレンダーに登録するアドオン情報
bl_info = {
    "name": "Level Editor",
    "author": "Taro Kamata",
    "version": (1, 0),
    "blender": (3, 3, 1),
    "location": "",
    "description": "Level Editor",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object"
}

# トップバーの拡張メニュー
class TOPBAR_MT_my_menu(bpy.types.Menu):
    # Blenderがクラスを識別する為の固有の文字列
    bl_idname = "TOPBAR_MT_my_menu"
    # メニューのラベルとして表示される文字列
    bl_label = "MyMenu"
    # 著者表示用の文字列
    bl_description = "Level Editor - by " + bl_info["author"]

    # サブメニューの描画
    def draw(self, context):
        # トップバーの「エディターメニュー」に項目(オペレータ)を追加
        self.layout.operator("wm.url_open_preset", text="Manual", icon='HELP')

    # 既存のメニューにサブメニューを追加するための関数
    def submenu(self, context):
        # ID指定でサブメニューを追加
        self.layout.menu(TOPBAR_MT_my_menu.bl_idname)

# 登録するクラスのリスト
classes = (
    TOPBAR_MT_my_menu,
)

# アドオン有効化時コールバック
def register():
    # クラスをBlenderに登録
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # メニューに項目を追加（TOPBAR_MT_my_menuのsubmenuメソッドを登録）
    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_my_menu.submenu)
    print("レベルエディタが有効化されました。")

# アドオン無効化時コールバック
def unregister():
    # メニューから項目を削除
    bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_my_menu.submenu)
    
    # Blenderからクラスを削除
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("レベルエディタが無効化されました。")

# テスト用コード
if __name__ == "__main__":
    register()
