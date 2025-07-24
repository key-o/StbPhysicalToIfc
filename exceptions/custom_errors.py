"""カスタム例外クラス定義"""


class ConversionError(Exception):
    """変換処理における一般的なエラー"""
    pass


class FileNotFoundError(ConversionError):
    """ファイルが見つからないエラー"""
    pass


class FileSizeError(ConversionError):
    """ファイルサイズが制限を超えたエラー"""
    pass


class XMLParseError(ConversionError):
    """XML解析エラー"""
    pass


class ElementValidationError(ConversionError):
    """要素検証エラー"""
    pass


class IFCGenerationError(ConversionError):
    """IFC生成エラー"""
    pass


class Stb2IfcError(ConversionError):
    """STB to IFC変換API専用エラー"""
    pass


# Phase 2: システム信頼性向上のための追加例外クラス

class ParameterValidationError(ElementValidationError):
    """パラメータ検証エラー"""
    def __init__(self, element_type: str, parameter_name: str, message: str = ""):
        self.element_type = element_type
        self.parameter_name = parameter_name
        if not message:
            message = f"{element_type}の{parameter_name}パラメータに問題があります"
        super().__init__(message)


class GeometryValidationError(ElementValidationError):
    """ジオメトリ検証エラー"""
    def __init__(self, element_type: str, geometry_issue: str, message: str = ""):
        self.element_type = element_type
        self.geometry_issue = geometry_issue
        if not message:
            message = f"{element_type}のジオメトリに問題があります: {geometry_issue}"
        super().__init__(message)


class SectionTypeNotSupportedError(ConversionError):
    """未対応断面タイプエラー"""
    def __init__(self, section_type: str, element_type: str = "", message: str = ""):
        self.section_type = section_type
        self.element_type = element_type
        if not message:
            if element_type:
                message = f"{element_type}の断面タイプ'{section_type}'はサポートされていません"
            else:
                message = f"断面タイプ'{section_type}'はサポートされていません"
        super().__init__(message)


class MaterialDataError(ConversionError):
    """材料データエラー"""
    def __init__(self, material_name: str, issue: str = "", message: str = ""):
        self.material_name = material_name
        self.issue = issue
        if not message:
            if issue:
                message = f"材料'{material_name}'のデータに問題があります: {issue}"
            else:
                message = f"材料'{material_name}'のデータに問題があります"
        super().__init__(message)


class NodeRelationError(ConversionError):
    """ノード関連エラー"""
    def __init__(self, node_id: str, issue: str = "", message: str = ""):
        self.node_id = node_id
        self.issue = issue
        if not message:
            if issue:
                message = f"ノード'{node_id}'の関連付けに問題があります: {issue}"
            else:
                message = f"ノード'{node_id}'の関連付けに問題があります"
        super().__init__(message)


class StoryAssignmentError(ConversionError):
    """階層割り当てエラー"""
    def __init__(self, element_id: str, story_info: str = "", message: str = ""):
        self.element_id = element_id
        self.story_info = story_info
        if not message:
            if story_info:
                message = f"要素'{element_id}'の階層割り当てに問題があります: {story_info}"
            else:
                message = f"要素'{element_id}'の階層割り当てに問題があります"
        super().__init__(message)


class ProfileCreationError(IFCGenerationError):
    """プロファイル作成エラー"""
    def __init__(self, profile_type: str, parameters: dict = None, message: str = ""):
        self.profile_type = profile_type
        self.parameters = parameters or {}
        if not message:
            message = f"プロファイル'{profile_type}'の作成に失敗しました"
        super().__init__(message)


class CoordinateSystemError(GeometryValidationError):
    """座標系エラー"""
    def __init__(self, coordinate_info: str = "", message: str = ""):
        self.coordinate_info = coordinate_info
        if not message:
            if coordinate_info:
                message = f"座標系の処理に問題があります: {coordinate_info}"
            else:
                message = "座標系の処理に問題があります"
        super().__init__("coordinate_system", coordinate_info, message)