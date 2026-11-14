"""Independent source examples exercise arithmetic, scope, joins and saved revisions."""
import copy
import csv
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from server import native_query as nq, schedule_planner as sp, quantities, store
from tests import test_backend_upgrade as backend_fixture


class QueryOperations(unittest.TestCase):
    def setUp(self):
        self.doc={'objects':[
            {'id':'x','type':'room','label':'Office','page':1,'properties':{'department':'A','net_area_m2':10}},
            {'id':'y','type':'room','label':'Store','page':1,'properties':{'department':'A','net_area_m2':5}},
            {'id':'z','type':'room','label':'Office','page':1,'properties':{'department':'B','net_area_m2':25}},
        ]}
    def plan(self,**extra):
        return {'answerable':True,'object_type':'room','object_ids':None,'filters':[],
                'aggregate':'sum','property':'properties.net_area_m2','explanation':'Source areas',**extra}
    def test_grouping_and_exclusion_preserve_operand_ids(self):
        result=nq.execute(self.plan(aggregate='group_sum',group_by='properties.department'),self.doc)
        self.assertEqual([(r['label'],r['value']) for r in result['rows']],[('A',15),('B',25)])
        self.assertEqual(result['rows'][0]['object_ids'],['x','y'])
        result=nq.execute(self.plan(filters=[{'field':'label','operator':'not_equals','value':'Store'}]),self.doc)
        self.assertEqual(result['value'],35)
    def test_or_groups_and_boolean_filters_cannot_widen_to_other_values(self):
        result=nq.execute(self.plan(aggregate='count',filters=[{'field':'label','operator':'one_of','value':['Office','Studio']}]),self.doc)
        self.assertEqual(result['value'],2)
        self.doc['objects'][0]['properties']['external']=False
        self.doc['objects'][1]['properties']['external']=0
        self.assertIsNone(nq.execute(self.plan(aggregate='count',filters=[{'field':'properties.external','operator':'equals','value':False}]),self.doc))
    def test_percentages_ratio_and_signed_difference_use_both_sources(self):
        comparison={'object_type':'room','object_ids':None,'filters':[],'aggregate':'sum','property':'properties.net_area_m2'}
        plan=self.plan(aggregate='percentage',object_ids=['x'],comparison=comparison)
        self.assertEqual(nq.execute(plan,self.doc)['value'],25)
        plan['aggregate']='ratio'
        self.assertEqual(nq.execute(plan,self.doc)['value'],.25)
        plan['aggregate']='difference'
        self.assertEqual(nq.execute(plan,self.doc)['value'],-30)
        self.assertEqual(len(nq.execute(plan,self.doc)['objects']),3)
    def test_invalid_denominator_and_missing_group_field_are_refused(self):
        comp={'object_type':'room','object_ids':None,'filters':[{'field':'label','operator':'equals','value':'absent'}],'aggregate':'count','property':None}
        self.assertIsNone(nq.execute(self.plan(aggregate='ratio',property=None,comparison=comp),self.doc))
        self.assertIsNone(nq.execute(self.plan(aggregate='group_sum',group_by='properties.missing'),self.doc))
    def test_units_nested_quantities_and_unresolved_dimensions(self):
        self.doc['objects']=[
            {'id':'a','type':'panel','properties':{'area':{'value':2,'unit':'m2'}}},
            {'id':'b','type':'panel','properties':{'area':{'value':10000,'unit':'cm2'}}}]
        found=nq.execute(self.plan(object_type='panel',property='properties.area'),self.doc)
        self.assertEqual((found['value'],found['unit']),(3,'m²'))
        found=nq.execute(self.plan(object_type='panel',property='properties.area',output_unit='ft2'),self.doc)
        self.assertAlmostEqual(found['value'],32.291731,places=5)
        self.doc['objects'][1]['properties']['area']['unit']='m'
        self.assertIsNone(nq.execute(self.plan(object_type='panel',property='properties.area'),self.doc))
    def test_previous_selection_enters_planning_and_cache_identity(self):
        saved={};calls=[]
        def request(content,**kw):
            calls.append(content)
            return self.plan(object_ids=['x'])
        prior={'question':'Show Office rooms','evidence':[{'id':'x'}],'calculation':{'operand_ids':['x']}}
        result=nq.answer('How much area do those have?',self.doc,request,(saved.get,saved.__setitem__),previous=prior)
        self.assertEqual(result['value'],10)
        self.assertIn('previous_turn',calls[0][0]['text'])
        nq.answer('How much area do those have?',self.doc,request,(saved.get,saved.__setitem__),previous=prior)
        self.assertEqual(len(calls),1)
        prior['evidence']=[{'id':'z'}]
        nq.answer('How much area do those have?',self.doc,request,(saved.get,saved.__setitem__),previous=prior)
        self.assertEqual(len(calls),2)
    def test_ambiguity_returns_a_question_instead_of_a_guessed_quantity(self):
        result=nq.answer('What is its area?',self.doc,lambda *a,**kw:{'answerable':False,'clarification':'Which room do you mean?','explanation':'More than one room.'})
        self.assertEqual(result['status'],'needs_clarification')
        self.assertIsNone(result['value'])


class ScheduleOperations(unittest.TestCase):
    def setUp(self):
        self.tables=[{'title':'DOOR SCHEDULE','page':1,'header':['Mark','Qty','Material','Width'],
                      'rows':[{'id':'a','cells':['D1','3','Timber','3\' - 0"'],'bbox':[0,0,1,.1]},
                              {'id':'b','cells':['D2','2','Steel','900 mm'],'bbox':[0,.1,1,.2]}]}]
    def plan(self,**kw):
        return {'answerable':True,'table':0,'filters':[],'aggregate':'sum_column','value_columns':[1],
                'multiplier_column':None,'explanation':'Sum scheduled items',**kw}
    def test_item_count_and_row_count_are_distinct(self):
        self.assertEqual(sp.execute(self.plan(),self.tables)['value'],5)
        self.assertEqual(sp.execute(self.plan(aggregate='count_rows',value_columns=[]),self.tables)['value'],2)
    def test_material_total_multiplies_quantity_by_each_dimensioned_width(self):
        found=sp.execute(self.plan(aggregate='sum_product_columns',value_columns=[1,3],output_unit='mm'),self.tables)
        self.assertEqual(found['value'],4543.2)
        self.assertAlmostEqual(found['terms'][0],2743.2)
        self.assertAlmostEqual(found['terms'][1],1800.0)
    def test_imperial_fraction_and_decimal_comma(self):
        self.assertAlmostEqual(quantities.parse('5\' - 11 1/2"')['value'],1.8161)
        self.assertAlmostEqual(quantities.parse('35 1/2"')['value'],.9017)
        self.assertEqual(quantities.parse('7,25 m²')['value'],7.25)
        self.assertEqual(quantities.parse('1.234,50 m²')['value'],1234.5)
        found=sp.execute(self.plan(value_columns=[3],output_unit='mm'),self.tables)
        self.assertAlmostEqual(found['value'],1814.4)
        self.assertEqual(found['unit'],'mm')
    def test_missing_units_prose_and_invalid_operators_do_not_become_counts(self):
        self.assertIsNone(quantities.parse('Width 900'))
        self.assertIsNone(quantities.parse('900','Width'))
        self.tables[0]['rows'][0]['cells'][1]='3 doors noted'
        self.assertIsNone(sp.execute(self.plan(),self.tables))
        self.assertIsNone(sp.execute(self.plan(filters=[{'column':0,'op':'arbitrary','values':['D']}]),self.tables))
        self.assertIsNone(sp.execute(self.plan(value_columns=[True]),self.tables))
    def test_material_groups_and_dimensioned_numeric_filters(self):
        found=sp.execute(self.plan(aggregate='group_sum_column',group_column=2),self.tables)
        self.assertEqual([(r['label'],r['value']) for r in found['groups']],[('Steel',2),('Timber',3)])
        found=sp.execute(self.plan(filters=[{'column':3,'op':'gt','values':['910 mm']}]),self.tables)
        self.assertEqual(found['value'],3)
    def test_cross_sheet_join_cites_both_pages_and_refuses_ambiguous_key(self):
        self.tables.append({'title':'DOOR TYPE SCHEDULE','page':4,'header':['Mark','Rating'],
                            'rows':[{'id':'type-d1','cells':['D1','EI60'],'bbox':[.1,.2,.3,.4]}]})
        plan=self.plan(filters=[{'column':0,'op':'equals','values':['D1']}],aggregate='join_value',value_columns=[1],
                       join={'table':1,'left_column':0,'right_column':0})
        result=sp.answer('What rating is the scheduled D1?',{'metadata':{'schedule_tables':self.tables}},
                         request=lambda *a,**kw:plan)
        self.assertEqual(result['value'],'Rating: EI60')
        self.assertEqual([o['page'] for o in result['evidence']],[1,4])
        self.tables[1]['rows'].append({'id':'duplicate','cells':['D1','EI30']})
        self.assertIsNone(sp.execute(plan,self.tables))


class ReviewReceipts(unittest.TestCase):
    setUp=backend_fixture.BackendUpgrade.setUp
    tearDown=backend_fixture.BackendUpgrade.tearDown
    ask=backend_fixture.BackendUpgrade.ask
    def test_old_process_cannot_claim_edited_code_is_loaded(self):
        with patch('server.app._source_revision',return_value='new-unloaded-revision'):
            response=self.ask(mode='native')
        self.assertEqual(response.status_code,503)
        self.assertIn('Restart',response.json()['detail']['message'])
    def saved(self):
        result={'id':'review-test','document_id':self.doc['id'],'question':'Count windows','value':2,'unit':'count',
                'category':'window','can_review':True,'operation':'count','evidence':[
                    {'id':'w1','document_id':self.doc['id'],'label':'First window','page':1,'bbox':[.1,.1,.2,.2]},
                    {'id':'w2','document_id':self.doc['id'],'label':'Second window','page':1,'bbox':[.3,.1,.4,.2]}]}
        store.save_answer(result['id'],self.doc['id'],result['question'],result)
        return result
    def test_review_export_original_and_reload_are_one_revision(self):
        result=self.saved()
        body={'excluded_evidence_ids':['w1'],'base_revision':0}
        saved=self.client.post('/api/answers/review-test/review',json=body)
        self.assertEqual(saved.status_code,200)
        self.assertEqual(saved.json()['value'],1)
        self.assertIn('1 window',saved.json()['answer'])
        again=self.client.post('/api/answers/review-test/review',json=body)
        self.assertEqual(again.status_code,409)
        exported=self.client.get('/api/answers/review-test/export').json()
        self.assertEqual((exported['value'],exported['export_revision']),(1,'1.0'))
        self.assertEqual(store.read_answer(result['id'],original=True)['value'],2)
        self.assertEqual(self.client.get('/api/answers/review-test').json()['value'],1)
        csv_body=self.client.get('/api/answers/review-test/export?format=csv').text
        rows=list(csv.DictReader(io.StringIO(csv_body)))
        self.assertEqual(rows[0]['value'],'1')
        self.assertEqual([r['included'] for r in rows[1:]],['False','True'])
    def test_export_neutralizes_spreadsheet_formulas(self):
        result=self.saved();result['question']='=SUM(A1:A2)'
        store.update_answer(result['id'],result)
        body=self.client.get('/api/answers/review-test/export?format=csv').text
        self.assertTrue(list(csv.DictReader(io.StringIO(body)))[0]['question'].startswith("'="))
    def test_context_from_other_drawing_is_rejected(self):
        result=self.saved()
        with patch('server.app.extracted',return_value=self.native):
            response=self.ask(previous_answer_id=result['id'],mode='native')
        self.assertEqual(response.status_code,409)


if __name__=='__main__':
    unittest.main()
