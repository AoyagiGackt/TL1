import bpy
import math
import bpy_extras
import gpu
import gpu_extras.batch
import copy

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
class MYADDON_OT_export_scene(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    bl_idname = "myaddon.myaddon_ot_export_scene"
    bl_label = "シーン出力"
    bl_description = "シーン情報をExportします"
    filename_ext = ".scene"
    bl_options = {'REGISTER', 'UNDO'}
    
    def write_and_print(self, file, text):
        print(text)          # コンソールに出力
        file.write(text + "\n") # ファイルに書き込み
    
    def parse_scene_recursive(self, file, object, level):
        """シーン解析用再帰関数"""
        indent = "\t" * level

        # オブジェクトのタイプのみを出力 (例: MESH)
        self.write_and_print(file, indent + object.type)
        
        # トランスフォーム情報の抽出と変換
        trans, rot, scale = object.matrix_local.decompose()
        rot = rot.to_euler()
        rot_x = math.degrees(rot.x)
        rot_y = math.degrees(rot.y)
        rot_z = math.degrees(rot.z)
        
        # 指定されたフォーマット (T, R, S) で出力
        self.write_and_print(file, indent + "T %f %f %f" % (trans.x, trans.y, trans.z))
        self.write_and_print(file, indent + "R %f %f %f" % (rot_x, rot_y, rot_z))
        self.write_and_print(file, indent + "S %f %f %f" % (scale.x, scale.y, scale.z))
        
        # カスタムプロパティ 'file_name' があれば N として出力
        if "file_name" in object:
            self.write_and_print(file, indent + "N %s" % object["file_name"])
            
        # オブジェクトデータの終了を示す END を出力
        self.write_and_print(file, indent + 'END')
        self.write_and_print(file, '')
        
        # 子ノードへ進む（深さが1上がる）
        for child in object.children:
            self.parse_scene_recursive(file, child, level + 1)

    def export(self):
        print("シーン情報出力開始…%r"%self.filepath)
        self.file = open(self.filepath, "wt", encoding="utf-8")
        self.file.write("SCENE\n\n")

    def execute(self, context):
        print("シーン情報をExportします")
        self.export()
        
        for object in bpy.context.scene.objects:
            if object.parent:
                continue
            self.parse_scene_recursive(self.file, object, 0)
            
        self.file.close()
        print("シーン情報をExportしました")
        self.report({'INFO'}, "シーン情報をExportしました")
        return {'FINISHED'}


# ICO球を生成するオペレータークラス
class MYADDON_OT_create_ico_sphere(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_create_object"
    bl_label = "ICO球生成"
    bl_description = "ICO球を生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.primitive_ico_sphere_add()
        print("ICO球を生成しました。")
        return {'FINISHED'}


# オペレータ カスタムプロパティ['file_name']
class MYADDON_OT_add_filename(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_add_filename"
    bl_label = "FileName 追加"
    bl_description = "['file_name']カスタムプロパティを追加します"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.object["file_name"] = ""
        return {"FINISHED"}


# オブジェクトのファイルネームパネルクラス
class OBJECT_PT_file_name(bpy.types.Panel):
    """オブジェクトのファイルネームパネル"""
    bl_idname = "OBJECT_PT_file_name"
    bl_label = "FileName"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        
        if "file_name" in context.object:
            layout.prop(context.object, '["file_name"]', text=self.bl_label)
        else:
            layout.operator(MYADDON_OT_add_filename.bl_idname)


# トップバーの拡張メニュー
class TOPBAR_MT_my_menu(bpy.types.Menu):
    bl_idname = "TOPBAR_MT_my_menu"
    bl_label = "MyMenu"
    bl_description = "Level Editor - by " + bl_info["author"]

    def draw(self, context):
        layout = self.layout
        layout.operator("wm.url_open_preset", text="Manual", icon='HELP')
        layout.separator()
        layout.operator(MYADDON_OT_create_ico_sphere.bl_idname, text="ICO球生成", icon='MESH_ICOSPHERE')
        layout.operator(MYADDON_OT_export_scene.bl_idname, text="シーン出力", icon='EXPORT')

    def submenu(self, context):
        self.layout.menu(TOPBAR_MT_my_menu.bl_idname)


# コライダー描画クラス
class DrawCollider:
    # 描画ハンドル
    handle = None

    # 3Dビューに登録する描画関数
    @staticmethod
    def draw_collider():
        
        # 頂点データとインデックスデータを空リストで初期化
        vertices = {"pos": []}
        indices = []

        # 各頂点の、オブジェクト中心からのオフセット
        offsets = [
            [-0.5, -0.5, -0.5], #左手前
            [+0.5, -0.5, -0.5], #右手前
            [-0.5, +0.5, -0.5], #左上前
            [+0.5, +0.5, -0.5], #右上前
            [-0.5, -0.5, +0.5], #左手奥
            [+0.5, -0.5, +0.5], #右手奥
            [-0.5, +0.5, +0.5], #左上奥
            [+0.5, +0.5, +0.5], #右上奥
        ]

        # 立方体のX, Y, Z方向サイズ
        size = [2, 2, 2]

        # 現在シーンのオブジェクトリストを走査
        for object in bpy.context.scene.objects:
            # 追加前の頂点数
            start = len(vertices["pos"])

            # Boxの8頂点分回す
            for offset in offsets:
                # オブジェクトの中心座標をコピー
                pos = copy.copy(object.location)
                # 中心点を基準に各頂点ごとにずらす
                pos[0] += offset[0] * size[0]
                pos[1] += offset[1] * size[1]
                pos[2] += offset[2] * size[2]
                # 頂点データリストに座標を追加
                vertices['pos'].append(pos)

            # 前面を構成する辺の頂点インデックス
            indices.append([start + 0, start + 1])
            indices.append([start + 2, start + 3])
            indices.append([start + 0, start + 2])
            indices.append([start + 1, start + 3])
            # 奥面を構成する辺の頂点インデックス
            indices.append([start + 4, start + 5])
            indices.append([start + 6, start + 7])
            indices.append([start + 4, start + 6])
            indices.append([start + 5, start + 7])
            # 手前と奥を繋ぐ辺の頂点インデックス
            indices.append([start + 0, start + 4])
            indices.append([start + 1, start + 5])
            indices.append([start + 2, start + 6])
            indices.append([start + 3, start + 7])

        # 描画対象のオブジェクトが1つもない場合は処理をスキップ
        if not vertices["pos"]:
            return

        # ビルトインのシェーダを取得
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        
        # バッチを作成
        batch = gpu_extras.batch.batch_for_shader(shader, "LINES", vertices, indices=indices)

        # シェーダのパラメータ設定
        color = [0.5, 1.0, 1.0, 1.0]
        shader.bind()
        shader.uniform_float("color", color)
        
        # 描画
        batch.draw(shader)


# 登録するクラスのリスト
classes = (
    MYADDON_OT_create_ico_sphere,
    MYADDON_OT_export_scene,
    TOPBAR_MT_my_menu,
    MYADDON_OT_add_filename,
    OBJECT_PT_file_name,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_my_menu.submenu)
    
    DrawCollider.handle = bpy.types.SpaceView3D.draw_handler_add(
        DrawCollider.draw_collider, (), "WINDOW", "POST_VIEW"
    )
    print("レベルエディタが有効化されました。")

def unregister():
    bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_my_menu.submenu)
    
    if DrawCollider.handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(DrawCollider.handle, "WINDOW")
        DrawCollider.handle = None
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("レベルエディタが無効化されました。")

if __name__ == "__main__":
    register()
