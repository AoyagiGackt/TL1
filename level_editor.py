import bpy
import math
import bpy_extras
import gpu
import gpu_extras.batch
import copy
import mathutils
import json

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

# シーン情報をJSON形式で出力するオペレータークラス
class MYADDON_OT_export_scene(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    bl_idname = "myaddon.myaddon_ot_export_scene"
    bl_label = "シーン出力"
    bl_description = "シーン情報をExportします"
    
    # 出力するファイルの拡張子を .json に
    filename_ext = ".json"
    bl_options = {'REGISTER', 'UNDO'}
    
    def parse_scene_recursive_json(self, data_parent, object, level):
        """シーン解析用JSON再帰関数"""
        
        # シーンのオブジェクト1個分のjsonオブジェクト生成
        json_object = dict()
        
        # オブジェクト種類とオブジェクト名
        json_object["type"] = object.type
        json_object["name"] = object.name
        
        # オブジェクトのローカルトランスフォームから平行移動、回転、スケールを抽出
        trans, rot, scale = object.matrix_local.decompose()
        # 回転を Quaternion から Euler (3軸での回転角) に変換
        rot = rot.to_euler()
        # ラジアンから度数法に変換
        rot.x = math.degrees(rot.x)
        rot.y = math.degrees(rot.y)
        rot.z = math.degrees(rot.z)
        
        # トランスフォーム情報をディキシナリに登録
        transform = dict()
        transform["translation"] = (trans.x, trans.y, trans.z)
        transform["rotation"] = (rot.x, rot.y, rot.z)
        transform["scaling"] = (scale.x, scale.y, scale.z)
        
        # まとめて1個分のjsonオブジェクトに登録
        json_object["transform"] = transform
        
        # カスタムプロパティ 'file_name'
        if "file_name" in object:
            json_object["file_name"] = object["file_name"]
            
        # カスタムプロパティ 'collider'
        if "collider" in object:
            collider = dict()
            collider["type"] = object["collider"]
            collider["center"] = object["collider_center"].to_list() # Vectorをリストに変換
            collider["size"] = object["collider_size"].to_list()     # Vectorをリストに変換
            json_object["collider"] = collider
            
        # 1個分のjsonオブジェクトを親オブジェクトに登録
        data_parent.append(json_object)
        
        # 子ノードがあれば直接の子供リストを走査して再帰処理
        if len(object.children) > 0:
            # 子ノードリストを作成
            json_object["children"] = list()
            for child in object.children:
                self.parse_scene_recursive_json(json_object["children"], child, level + 1)

    def export_json(self):
        """JSON形式でファイルに出力"""
        
        # 保存する情報をまとめるdict
        json_object_root = dict()
        
        # ノード名
        json_object_root["name"] = "scene"
        # オブジェクトリストを作成
        json_object_root["objects"] = list()
        
        # シーン内の全オブジェクトについて走査してパック
        for object in bpy.context.scene.objects:
            # 親オブジェクトがあるものはスキップ（代わりに親から呼び出すから）
            if object.parent:
                continue
            # シーン直下のオブジェクトをルートノード(深さ0)とし、再帰関数で走査
            self.parse_scene_recursive_json(json_object_root["objects"], object, 0)
            
        # オブジェクトをJSON文字列にエンコード（改行・インデント付き）
        json_text = json.dumps(json_object_root, ensure_ascii=False, cls=json.JSONEncoder, indent=4)
        
        # コンソールに表示してみる
        print(json_text)
        
        # ファイルをテキスト形式で書き出し用にオープン（スコープを抜けると自動的にクローズされる）
        with open(self.filepath, "wt", encoding="utf-8") as file:
            # ファイルに文字列を書き込む
            file.write(json_text)

    def execute(self, context):
        print("シーン情報をExportします")
        
        # JSON出力関数の呼び出し
        self.export_json()
        
        self.report({'INFO'}, "シーン情報をExportしました")
        print("シーン情報をExportしました")
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


# オペレータ カスタムプロパティ['collider']
class MYADDON_OT_add_collider(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_add_collider"
    bl_label = "コライダー 追加"
    bl_description = "['collider']カスタムプロパティを追加します"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        context.object["collider"] = "BOX"
        context.object["collider_center"] = mathutils.Vector((0.0, 0.0, 0.0))
        context.object["collider_size"] = mathutils.Vector((2.0, 2.0, 2.0))
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


# パネル コライダー
class OBJECT_PT_collider(bpy.types.Panel):
    """オブジェクトのコライダーパネル"""
    bl_idname = "OBJECT_PT_collider"
    bl_label = "Collider"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        layout = self.layout

        if "collider" in context.object:
            layout.prop(context.object, '["collider"]', text="Type")
            layout.prop(context.object, '["collider_center"]', text="Center")
            layout.prop(context.object, '["collider_size"]', text="Size")
        else:
            layout.operator(MYADDON_OT_add_collider.bl_idname)


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
        vertices = {"pos": []}
        indices = []

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

        for object in bpy.context.scene.objects:
            if not "collider" in object:
                continue

            center = mathutils.Vector((0.0, 0.0, 0.0))
            size = mathutils.Vector((2.0, 2.0, 2.0))

            center[0] = object["collider_center"][0]
            center[1] = object["collider_center"][1]
            center[2] = object["collider_center"][2]
            size[0] = object["collider_size"][0]
            size[1] = object["collider_size"][1]
            size[2] = object["collider_size"][2]

            start = len(vertices["pos"])

            for offset in offsets:
                pos = copy.copy(center)
                pos[0] += offset[0] * size[0]
                pos[1] += offset[1] * size[1]
                pos[2] += offset[2] * size[2]
                pos = object.matrix_world @ pos
                vertices['pos'].append(pos)

            indices.append([start + 0, start + 1])
            indices.append([start + 2, start + 3])
            indices.append([start + 0, start + 2])
            indices.append([start + 1, start + 3])
            indices.append([start + 4, start + 5])
            indices.append([start + 6, start + 7])
            indices.append([start + 4, start + 6])
            indices.append([start + 5, start + 7])
            indices.append([start + 0, start + 4])
            indices.append([start + 1, start + 5])
            indices.append([start + 2, start + 6])
            indices.append([start + 3, start + 7])

        if not vertices["pos"]:
            return

        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        batch = gpu_extras.batch.batch_for_shader(shader, "LINES", vertices, indices=indices)

        color = [0.5, 1.0, 1.0, 1.0]
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)


# 登録するクラスのリスト
classes = (
    MYADDON_OT_create_ico_sphere,
    MYADDON_OT_export_scene,
    TOPBAR_MT_my_menu,
    MYADDON_OT_add_filename,
    OBJECT_PT_file_name,
    MYADDON_OT_add_collider,
    OBJECT_PT_collider,
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
