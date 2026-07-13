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

class MYADDON_OT_import_level01(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = "myaddon.myaddon_ot_import_level01"
    bl_label = "レベルデータの読み込み"
    bl_description = "JSONファイルを汎用的に読み込みます"
    
    filepath: bpy.props.StringProperty(default="level01.json")
    filename_ext = ".json"
    
    # position系のキーはオブジェクト自身の位置として消費するので、
    # スポーン地点マーカー化の対象からは除外する
    POSITION_KEYS = ["translation", "position", "pos", "location"]

    # JSON上の軸名 -> Blender座標系でその軸方向へ1ステップ進めるベクトル
    AXIS_STEP_VECTOR = {
        "x": mathutils.Vector((1.0, 0.0, 0.0)),
        "y": mathutils.Vector((0.0, 0.0, 1.0)),
        "z": mathutils.Vector((0.0, 1.0, 0.0)),
    }

    def json_pos_to_blender(self, data_dict):
        """position系のキー（JSON: Y軸が上）をBlenderの座標系（Z軸が上）に変換する"""
        for pos_key in self.POSITION_KEYS:
            if pos_key in data_dict and isinstance(data_dict[pos_key], list) and len(data_dict[pos_key]) >= 3:
                x, y, z = data_dict[pos_key][0], data_dict[pos_key][1], data_dict[pos_key][2]
                return [x, z, y]
        return [0.0, 0.0, 0.0]

    def create_blender_object(self, data_dict, parent=None):
        """1つのデータからオブジェクトを生成し、すべてのキーをカスタムプロパティに保存する"""
        # オブジェクト名になりそうなキーを自動検索（なければデータ型を名前にする）
        obj_name = data_dict.get("name") or data_dict.get("comment") or data_dict.get("type") or "ImportedObject"

        # 位置になりそうなキーを自動検索（XYZの3要素リスト）
        loc = self.json_pos_to_blender(data_dict)

        # とりあえず配置用の空オブジェクトを作成
        bpy.ops.object.empty_add(type='CUBE', radius=0.5, location=loc)
        new_obj = bpy.context.object
        new_obj.name = str(obj_name)

        if parent:
            new_obj.parent = parent
            new_obj.matrix_parent_inverse = parent.matrix_world.inverted()

        # JSON内にあるすべてのデータをカスタムプロパティとしてオブジェクトに丸ごと記憶させる
        for key, value in data_dict.items():
            # 子ノードリストそのまま保存できないので文字列化して保存
            if key == "children" or isinstance(value, (dict, list)):
                new_obj[key] = json.dumps(value, ensure_ascii=False)
            else:
                new_obj[key] = value

        return new_obj

    def create_blender_row(self, data_dict, parent=None):
        """type="row" のデータを、position起点からaxis方向にcount個・step間隔で実際に並べて生成する"""
        obj_name = data_dict.get("comment") or data_dict.get("name") or "row"

        base_loc = mathutils.Vector(self.json_pos_to_blender(data_dict))
        axis = data_dict.get("axis", "x")
        count = int(data_dict.get("count", 1))
        step = float(data_dict.get("step", 1.0))
        step_vector = self.AXIS_STEP_VECTOR.get(axis, self.AXIS_STEP_VECTOR["x"])

        # 行全体をまとめる親エンプティ（メタ情報はここに保持）
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=0.5, location=base_loc)
        row_obj = bpy.context.object
        row_obj.name = str(obj_name)
        if parent:
            row_obj.parent = parent
            row_obj.matrix_parent_inverse = parent.matrix_world.inverted()

        for key, value in data_dict.items():
            if key == "children" or isinstance(value, (dict, list)):
                row_obj[key] = json.dumps(value, ensure_ascii=False)
            else:
                row_obj[key] = value

        # count個分のブロックを実際に等間隔配置
        for i in range(count):
            block_loc = base_loc + step_vector * (step * i)
            bpy.ops.object.empty_add(type='CUBE', radius=0.5, location=block_loc)
            block_obj = bpy.context.object
            block_obj.name = f"{obj_name}_{i:02d}"
            block_obj.parent = row_obj
            block_obj.matrix_parent_inverse = row_obj.matrix_world.inverted()

        return row_obj

    def create_spawn_marker(self, name, position, parent=None):
        """[x, y, z] 形式の座標配列をスポーン地点マーカーとして生成する"""
        x, y, z = position
        bpy.ops.object.empty_add(type='SPHERE', radius=0.3, location=(x, z, y))
        marker = bpy.context.object
        marker.name = str(name)
        if parent:
            marker.parent = parent
            marker.matrix_parent_inverse = parent.matrix_world.inverted()
        return marker

    def parse_any_json_recursive(self, data, parent=None):
        """どんな構造のJSONでも再帰的に走査してBlenderオブジェクト化する"""
        if isinstance(data, dict):
            # type="row" ならブロックを実際に並べて生成、それ以外は単体オブジェクトとして生成
            if data.get("type") == "row" and "axis" in data and "count" in data:
                current_obj = self.create_blender_row(data, parent)
            else:
                current_obj = self.create_blender_object(data, parent)

            # 自身の下にさらに隠れた子リストやオブジェクト配列がないか探して再帰
            for key, value in data.items():
                if key == "children" or key in self.POSITION_KEYS:
                    continue
                # [x, y, z] のような座標そのものの配列は、子オブジェクトではなく
                # スポーン地点マーカーとして直接生成する（playerSpawn / enemySpawn など）
                if isinstance(value, list) and len(value) == 3 and all(isinstance(v, (int, float)) for v in value):
                    self.create_spawn_marker(key, value, current_obj)
                elif isinstance(value, (dict, list)):
                    self.parse_any_json_recursive(value, current_obj)

            # 子リスト構造があれば処理
            if "children" in data and isinstance(data["children"], list):
                for child_data in data["children"]:
                    self.parse_any_json_recursive(child_data, current_obj)

        elif isinstance(data, list):
            # 配列なら、中身をバラして走査
            for item in data:
                self.parse_any_json_recursive(item, parent)

    def execute(self, context):
        with open(self.filepath, "rt", encoding="utf-8") as file:
            data = json.load(file)
            
        print(f"--- {self.filepath} の汎用解析を開始 ---")
        
        # ルートから全自動解析
        self.parse_any_json_recursive(data)
            
        self.report({'INFO'}, "JSONデータを読み込み、プロパティを保持したオブジェクトを生成しました")
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
        layout.separator()
        layout.operator(MYADDON_OT_import_level01.bl_idname, text="レベルデータの読み込み", icon='IMPORT')
        
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
    MYADDON_OT_import_level01,
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