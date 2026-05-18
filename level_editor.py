import bpy
import math

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

# シーン情報を出力するオペレータークラス
class MYADDON_OT_export_scene(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_export_scene"
    bl_label = "シーン出力"
    bl_description = "シーン情報をExportします"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("シーン情報をExportします")
        
        # シーン内のオブジェクト情報をループしてコンソルに出力
        for object in bpy.context.scene.objects:
            print(object.type + " - " + object.name)
            #ローカルトランスフォーム行列から平行移動、回転、スケーリングを抽出
            # 型はVector, Quaternion, Vector
            trans, rot, scale = object.matrix_local.decompose()
            #回転を Quternion から Euler (3軸での回転角)に変換
            rot = rot.to_euler()
            #ラジアンから度数法に変換
            rot.x = math.degrees(rot.x)
            rot.y = math.degrees(rot.y)
            rot.z = math.degrees(rot.z)
            
            #トランスフォーム情報を表示
            print("Trans(%f,%f,%f)" % (trans.x, trans.y, trans. z) )
            print("Rot(%f,%f,%f)" % (rot.x, rot.y, rot.z) )
            print("Scale(%f,%f,%f)" % (scale.x, scale.y, scale.z) )
            #親オブジェクトの名前を表示
            if object.parent:
                print("Parent:" + object.parent.name)
            print()

        print("シーン情報をExportしました")
        self.report({'INFO'}, "シーン情報をExportしました")
        return {'FINISHED'}

# ICO球を生成するオペレータークラス
class MYADDON_OT_create_ico_sphere(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_create_object"
    bl_label = "ICO球生成"
    bl_description = "ICO球を生成します"
    bl_options = {'REGISTER', 'UNDO'}

    # メニューを実行したときに呼ばれる関数
    def execute(self, context):
        bpy.ops.mesh.primitive_ico_sphere_add()
        print("ICO球を生成しました。")
        return {'FINISHED'}

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
        layout = self.layout
        # トップバーの「エディターメニュー」に項目(オペレータ)を追加
        layout.operator("wm.url_open_preset", text="Manual", icon='HELP')
        
        layout.separator()
        
        layout.operator(MYADDON_OT_create_ico_sphere.bl_idname, text="ICO球生成", icon='MESH_ICOSPHERE')

        layout.operator(MYADDON_OT_export_scene.bl_idname, text="シーン出力", icon='EXPORT')

    # 既存のメニューにサブメニューを追加するための関数
    def submenu(self, context):
        # ID指定でサブメニューを追加
        self.layout.menu(TOPBAR_MT_my_menu.bl_idname)

# 登録するクラスのリスト
classes = (
    MYADDON_OT_export_scene,
    MYADDON_OT_create_ico_sphere,
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
