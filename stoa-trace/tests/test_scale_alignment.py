import unittest
from PIL import Image,ImageDraw
from server.scale_alignment import checker_endpoints


def source_bar(image,left=100,top=100):
    draw=ImageDraw.Draw(image)
    draw.rectangle((left,top,left+600,top+28),outline=0,width=1)
    for start,end,upper in ((0,75,False),(75,150,True),(150,300,False),(300,600,True)):
        draw.rectangle((left+start+1,top+(1 if upper else 14),left+end-1,top+(13 if upper else 27)),fill=0)


class CheckerScaleAlignment(unittest.TestCase):
    def test_unique_checker_bar_uses_source_edges_not_approximate_endpoints(self):
        image=Image.new('L',(900,240),255);source_bar(image)
        result=checker_endpoints(image,[[98,112],[704,112]])
        self.assertEqual(result['points'],[[100.,114.],[700.,114.]])
        self.assertGreater(result['pattern_support'],.9)

    def test_vertical_and_reversed_references_keep_their_direction(self):
        image=Image.new('L',(900,240),255);source_bar(image)
        reversed_result=checker_endpoints(image,[[704,112],[98,112]])
        self.assertEqual(reversed_result['points'],[[700.,114.],[100.,114.]])
        vertical=image.transpose(Image.Transpose.ROTATE_90)
        result=checker_endpoints(vertical,[[112,801],[112,195]])
        self.assertEqual(result['points'],[[114.,799.],[114.,199.]])

    def test_plain_lines_text_and_multiple_matching_bars_remain_unmodified(self):
        image=Image.new('L',(900,240),255);draw=ImageDraw.Draw(image)
        draw.line((100,114,700,114),fill=0,width=3)
        draw.text((300,80),'Scale 8 feet',fill=0)
        self.assertIsNone(checker_endpoints(image,[[98,112],[704,112]]))
        image=Image.new('L',(900,260),255);source_bar(image);source_bar(image,top=140)
        self.assertIsNone(checker_endpoints(image,[[98,112],[704,112]]))

    def test_unrelated_bar_at_wrong_span_or_angle_is_rejected(self):
        image=Image.new('L',(900,240),255);source_bar(image)
        self.assertIsNone(checker_endpoints(image,[[100,110],[400,110]]))
        self.assertIsNone(checker_endpoints(image,[[100,100],[700,180]]))
