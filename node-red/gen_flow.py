"""Generate a professional Node-RED flow (groups + function/switch/filter nodes)."""
import json, os

base = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(base, 'ui_template.html'), encoding='utf-8').read()

normalize_fn = """// Normalize & validate the raw scan from the dashboard
const p = msg.payload || {};
if (!p.food) { node.warn('empty scan dropped'); return null; }   // scenario: no food
const conf = Math.round((Number(p.confidence) || 0) * 1000) / 10;
msg.payload = {
    food: p.food,
    label: String(p.food).replace(/_/g, ' '),
    kcal: Number(p.kcal) || 0,
    protein: Number(p.protein) || 0,
    fat: Number(p.fat) || 0,
    carbs: Number(p.carbs) || 0,
    serving: p.serving || 'n/a',
    confidence: conf,
    time: new Date(p.ts || Date.now()).toISOString()
};
node.status({ fill: 'blue', shape: 'dot', text: msg.payload.label + ' (' + conf + '%)' });
return msg;"""

error_fn = """// Format any runtime error caught in this flow
msg.payload = {
    error: (msg.error && msg.error.message) || 'unknown error',
    source: (msg.error && msg.error.source && msg.error.source.id) || '',
    time: new Date().toISOString()
};
node.status({ fill: 'red', shape: 'ring', text: msg.payload.error });
return msg;"""

totals_fn = """// Running daily totals using flow context (resets each day)
const p = msg.payload;
const today = new Date().toISOString().slice(0, 10);
let s = flow.get('daily') || { date: today, kcal: 0, count: 0 };
if (s.date !== today) { s = { date: today, kcal: 0, count: 0 }; }
s.kcal += p.kcal;
s.count += 1;
flow.set('daily', s);
p.dailyTotalKcal = s.kcal;
p.scansToday = s.count;
node.status({ fill: 'green', shape: 'dot', text: s.count + ' scans · ' + s.kcal + ' kcal today' });
return msg;"""

nodes = [
  {'id':'food_flow','type':'tab','label':'Food Calorie Scanner','disabled':False,'info':''},
  {'id':'food_tab','type':'ui_tab','name':'Food Scanner','icon':'fa-cutlery','order':1},
  {'id':'food_group','type':'ui_group','name':'','tab':'food_tab','order':1,'disp':False,'width':24,'collapse':False},
  {'id':'food_base','type':'ui_base','theme':{'name':'theme-light'},'site':{'name':'Food Calorie Scanner','hideToolbar':'true','allowSwipe':'false','lockMenu':'false','dateFormat':'DD/MM/YYYY','sizes':{'sx':48,'sy':48,'gx':6,'gy':6,'cx':6,'cy':6,'px':0,'py':0}}},

  {'id':'food_template','type':'ui_template','z':'food_flow','g':'g_intake','group':'food_group','name':'Food Calorie Scanner','order':1,'width':24,'height':20,
   'format':html,'storeOutMessages':True,'fwdInMessages':True,'resendOnRefresh':True,'templateScope':'local','x':210,'y':200,'wires':[['fn_norm']]},
  {'id':'fn_norm','type':'function','z':'food_flow','g':'g_intake','name':'Normalize & validate','func':normalize_fn,'outputs':1,'noerr':0,'initialize':'','finalize':'','libs':[],'x':470,'y':200,'wires':[['sw_conf']]},

  {'id':'sw_conf','type':'switch','z':'food_flow','g':'g_route','name':'Confidence ≥ 60%?','property':'payload.confidence','propertyType':'msg',
   'rules':[{'t':'gte','v':'60','vt':'num'},{'t':'else'}],'checkall':'false','repair':False,'outputs':2,'x':710,'y':200,'wires':[['flt_dup'],['ch_low']]},
  {'id':'ch_low','type':'change','z':'food_flow','g':'g_route','name':'Flag low-confidence','rules':[{'t':'set','p':'payload.status','pt':'msg','to':'needs_review','tot':'str'}],'action':'','property':'','from':'','to':'','reg':False,'x':720,'y':320,'wires':[['dbg_low']]},

  {'id':'flt_dup','type':'rbe','z':'food_flow','g':'g_proc','name':'Skip repeat foods','func':'rbe','gap':'','start':'','inout':'out','septopics':True,'property':'payload.food','topi':'topic','x':960,'y':180,'wires':[['fn_totals']]},
  {'id':'fn_totals','type':'function','z':'food_flow','g':'g_proc','name':'Daily totals (context)','func':totals_fn,'outputs':1,'noerr':0,'initialize':'','finalize':'','libs':[],'x':1180,'y':180,'wires':[['json_str','dbg_ok']]},
  {'id':'json_str','type':'json','z':'food_flow','g':'g_proc','name':'to string','property':'payload','action':'str','pretty':False,'x':1400,'y':140,'wires':[['file_log']]},
  {'id':'file_log','type':'file','z':'food_flow','g':'g_proc','name':'log scans (jsonl)','filename':'food_scans.log','filenameType':'str','appendNewline':True,'overwriteFile':'false','encoding':'none','x':1590,'y':140,'wires':[[]]},
  {'id':'dbg_ok','type':'debug','z':'food_flow','g':'g_proc','name':'✓ logged','active':True,'tosidebar':True,'tostatus':False,'complete':'payload','targetType':'msg','x':1400,'y':220,'wires':[]},
  {'id':'dbg_low','type':'debug','z':'food_flow','g':'g_proc','name':'⚠ needs review','active':True,'tosidebar':True,'tostatus':False,'complete':'payload','targetType':'msg','x':970,'y':320,'wires':[]},

  # error handling — catches ANY runtime error in this flow
  {'id':'catch_err','type':'catch','z':'food_flow','g':'g_proc','name':'catch errors','scope':None,'uncaught':False,'x':960,'y':420,'wires':[['fn_err']]},
  {'id':'fn_err','type':'function','z':'food_flow','g':'g_proc','name':'format error','func':error_fn,'outputs':1,'noerr':0,'initialize':'','finalize':'','libs':[],'x':1180,'y':420,'wires':[['dbg_err']]},
  {'id':'dbg_err','type':'debug','z':'food_flow','g':'g_proc','name':'✗ flow error','active':True,'tosidebar':True,'tostatus':False,'complete':'payload','targetType':'msg','x':1400,'y':420,'wires':[]},
]

def box(members, pad=34, hw=98, hh=24):
    pts=[(n['x'],n['y']) for n in nodes if n.get('id') in members]
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    return (min(xs)-hw-pad, min(ys)-hh-pad,
            (max(xs)-min(xs))+2*hw+2*pad, (max(ys)-min(ys))+2*hh+2*pad)

groups = [
  ('g_intake','1 · Scan intake', ['food_template','fn_norm'], '#3a9b35','#dff0dd'),
  ('g_route', '2 · Confidence routing', ['sw_conf','ch_low'], '#c79a1e','#fbf2d0'),
  ('g_proc',  '3 · Filter, analytics, storage & errors', ['flt_dup','fn_totals','json_str','file_log','dbg_ok','dbg_low','catch_err','fn_err','dbg_err'], '#2d7fb8','#dcecf7'),
]
gnodes=[]
for gid,label,members,stroke,fill in groups:
    x,y,w,h=box(members)
    gnodes.append({'id':gid,'type':'group','z':'food_flow','name':label,
        'style':{'stroke':stroke,'stroke-opacity':'1','fill':fill,'fill-opacity':'0.4','label':True,'label-position':'nw','color':'#1a1a1a'},
        'nodes':members,'x':int(x),'y':int(y),'w':int(w),'h':int(h)})

out = [nodes[0]] + gnodes + nodes[1:]
json.dump(out, open(os.path.join(base,'flow.json'),'w',encoding='utf-8'), indent=2)
print('flow rebuilt: %d nodes incl %d groups (function x2, switch, rbe filter, change)' % (len(out), len(gnodes)))
