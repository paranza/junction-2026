import sys; sys.path.insert(0,".")
from mytab import *
for k in ("A801","A701","A700"):
    pg=pymupdf.open(D+P[k])[0]; M=pg.rotation_matrix
    bb=[pymupdf.Rect(i["bbox"])*M for i in pg.get_image_info()]
    print(k,len(bb),"min x0 of image placements:",round(min(b.x0 for b in bb)),"of page width",round(pg.rect.width), "total image area % of page:", round(100*sum(b.get_area() for b in bb)/pg.rect.get_area(),2))
