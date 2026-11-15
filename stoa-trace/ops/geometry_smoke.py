"""Offline smoke check for installed OCR models and source geometry. No LLM."""
from pathlib import Path
import json
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'server').exists():sys.path.insert(0,str(ROOT))


def run():
    from PIL import Image,ImageDraw,ImageFont
    from server.drawing_tools import DrawingSession
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'synthetic-geometry-smoke.png'
        image=Image.new('RGB',(1280,960),'white');draw=ImageDraw.Draw(image)
        draw.text((128,30),'Reference 10 m',font=ImageFont.load_default(size=42),fill='black')
        draw.line((128,192,768,192),fill='black',width=3)
        draw.line((200,400,1000,400,1000,800),fill='red',width=5)
        image.save(path)
        session=DrawingSession(path,1,[0,0,1,1])
        calibration=session.execute({'name':'calibrate','reference':{'points':[[.1,.2],[.6,.2]],
            'value':10,'unit':'m','quote':'10 m','annotation_bbox':[0,0,1,.15]}})
        network=session.execute({'name':'network','calibration_id':calibration['id'],'color':'red','region':[0,.3,1,1]})
        assert abs(network['value']-18.75)<.25,network['value']
        assert network['source_verified'] is False
        return {'status':'passed','real_ocr_calibration':True,'colored_centerline_graph':True,
                'measured_m':network['value'],'reference_m':18.75,'absolute_tolerance_m':.25,
                'model_calls':0,'fixture':'synthetic, not a real drawing accuracy score'}


if __name__=='__main__':print(json.dumps(run()))
