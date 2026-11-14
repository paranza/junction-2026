import unittest
from server import native_query
from server.native_qa import answer_native
from pathlib import Path


class NativeQueryTests(unittest.TestCase):
    def setUp(self):
        self.document={'metadata':{},'objects':[
            {'id':'a','type':'room','label':'Office','properties':{'room_number':'R1','net_area_m2':12.5}},
            {'id':'b','type':'room','label':'Office','properties':{'room_number':'R2','net_area_m2':31.75}},
            {'id':'c','type':'room','label':'Store','properties':{'room_number':'R3','net_area_m2':8.0}},
        ]}
    def plan(self, **values):
        return {'answerable':True,'object_type':'room','object_ids':None,'filters':[],
                'aggregate':'max','property':'properties.net_area_m2','explanation':'Compare source room areas',**values}
    def test_query_uses_full_native_collection_and_numeric_filters(self):
        result=native_query.execute(self.plan(aggregate='mean',filters=[{'field':'label','operator':'equals','value':'office'}]),self.document)
        self.assertEqual(result['value'],22.125)
        result=native_query.execute(self.plan(aggregate='count',property=None,filters=[{'field':'properties.net_area_m2','operator':'gt','value':10}]),self.document)
        self.assertEqual(result['value'],2)
    def test_missing_properties_and_invented_identifiers_fail_closed(self):
        self.assertIsNone(native_query.execute(self.plan(property='properties.gross_area_m2'),self.document))
        self.assertIsNone(native_query.execute(self.plan(object_ids=['invented']),self.document))
        self.assertIsNone(native_query.execute(self.plan(filters=[{'field':'properties.fire_rating','operator':'equals','value':'A'}]),self.document))
        self.document['objects'][1]['properties']['net_area_m2']=float('nan')
        self.assertIsNone(native_query.execute(self.plan(),self.document))
    def test_language_model_selects_plan_but_does_not_supply_answer_value(self):
        calls=[]
        def request(content,**options):
            calls.append(content)
            return self.plan()
        saved={}
        question='Which named space occupies the most square metres?'
        result=native_query.answer(question,self.document,request,(saved.get,saved.__setitem__))
        self.assertEqual(result['value'],31.75)
        self.assertEqual(result['evidence'][0]['id'],'b')
        self.assertEqual(result['calculation']['terms'],[12.5,31.75,8.0])
        self.document['objects'][1]['properties']['net_area_m2']=17.0
        changed=native_query.answer(question,self.document,request,(saved.get,saved.__setitem__))
        self.assertEqual(changed['value'],17.0)
        self.assertEqual(len(calls),2)
    def test_native_maximum_does_not_require_language_model(self):
        root=Path('/tmp')
        result=answer_native('What is the area of the largest labelled room?',self.document,root/'arbitrary.dxf',root)
        self.assertEqual(result['value'],31.75)
        self.assertEqual(result['calculation']['operation'],'max')
        minimum=answer_native('What is the area of the smallest labelled room?',self.document,root/'other-name.dxf',root)
        self.assertEqual(minimum['value'],8.0)
    def test_ranked_native_query_still_rejects_unsupported_conditions(self):
        root=Path('/tmp')
        self.assertIsNone(answer_native('What is the area of the largest room with wooden walls?',self.document,root/'arbitrary.dxf',root))

