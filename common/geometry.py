# common/geometry.py
"""
common.geometry
--------------
3D ジオメトリ関連のユーティリティを提供するモジュール。
"""


class Point3D:
    """
    三次元空間上の点を表現するクラス。

    Attributes:
        x (float): X 座標
        y (float): Y 座標
        z (float): Z 座標
    """

    def __init__(self, x, y, z):
        """
        コンストラクタ

        Args:
            x (float): X 座標
            y (float): Y 座標
            z (float): Z 座標
        """
        self.x = x
        self.y = y
        self.z = z

    def to_list(self):
        """座標をリスト形式で返す"""
        return [self.x, self.y, self.z]
