from PIL import Image,ImageDraw
import unittest
from server import symbol_proposals as sp


class SourceSymbolProposals(unittest.TestCase):
    def test_source_example_discovers_rotated_missed_objects_but_not_known_ones(self):
        symbol=Image.new('L',(34,42),255);draw=ImageDraw.Draw(symbol)
        draw.arc((4,5,29,36),-90,90,fill=100,width=2)
        draw.line((16,5,16,36),fill=100,width=2);draw.line((5,3,17,3),fill=100,width=2)
        source=Image.new('L',(700,500),255)
        for x,y,turn in [(70,70,0),(240,70,0),(420,240,90)]:source.paste(symbol.rotate(turn,expand=True),(x,y))
        ImageDraw.Draw(source).rectangle((250,300,330,350),outline=100,width=2)
        known=[{'label':'Seat on this source','bbox':[70/700,70/500,104/700,112/500]}]
        bank=sp.diverse_bank([],sp.examples(source,known))
        proposals=sp.discover(source,known,bank)
        centres=[((b['bbox'][0]+b['bbox'][2])/2,(b['bbox'][1]+b['bbox'][3])/2) for b in proposals]
        self.assertTrue(any(abs(x-257/700)<.025 and abs(y-91/500)<.025 for x,y in centres))
        self.assertTrue(any(abs(x-441/700)<.025 and abs(y-257/500)<.025 for x,y in centres))
        self.assertFalse(any(abs(x-87/700)<.025 and abs(y-91/500)<.025 for x,y in centres))
        self.assertTrue(all(p['proposal_only'] for p in proposals))

    def test_blank_examples_and_invalid_coordinates_do_not_create_objects(self):
        source=Image.new('L',(200,100),255)
        bank=sp.examples(source,[{'bbox':[0,0,.5,.5]},{'bbox':[0,0,2,1]}])
        self.assertEqual(bank,[]);self.assertEqual(sp.discover(source,[],bank),[])

    def test_unseen_form_touching_another_object_remains_a_reviewable_proposal(self):
        source=Image.new('L',(320,220),255);draw=ImageDraw.Draw(source)
        draw.ellipse((20,20,55,65),outline=170,width=2)
        draw.rounded_rectangle((140,80,175,130),radius=5,outline=170,width=2)
        draw.rectangle((175,80,260,145),outline=170,width=2)
        draw.text((90,20),'Room',fill=0)
        known=[{'label':'Located example','bbox':[18/320,18/220,57/320,67/220]}]
        style=sp.source_style(source,known)
        proposed=sp.unclaimed_components(source,known,style)
        self.assertTrue(any(abs((e['bbox'][0]+e['bbox'][2])/2-157.5/320)<.02 and
                            abs((e['bbox'][1]+e['bbox'][3])/2-105/220)<.02 for e in proposed))
        self.assertTrue(all(e['proposal_only'] for e in proposed))
        unsupported=sp.source_style(source,[{'bbox':[.02,.8,.1,.9]}])
        self.assertEqual(unsupported['unsupported_ids'],[0])
