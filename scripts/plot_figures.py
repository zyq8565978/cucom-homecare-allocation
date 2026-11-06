"""Publication plots of frozen aggregates; no smoothing or inference."""
from pathlib import Path
import json,csv,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap,Normalize
from matplotlib.patches import Rectangle,FancyArrowPatch
R=Path(__file__).resolve().parents[1];O=R/'results/figures';O.mkdir(parents=True,exist_ok=True)
F=json.loads((R/'data/display/figures.json').read_text(encoding='utf8'))
plt.rcParams.update({'font.family':'Arial','font.size':9.5,'axes.labelsize':9.5,'axes.titlesize':10.5,
 'axes.titleweight':'bold','axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,
 'xtick.labelsize':9,'ytick.labelsize':9,'xtick.major.width':.6,'ytick.major.width':.6,
 'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','savefig.facecolor':'white'})
BLUE='#285A78';ORANGE='#B96532';GRAY='#737B80';DARK='#262B30'
def save(fig,name):
    if len(sys.argv)>1 and name not in sys.argv[1:]:
        plt.close(fig);return
    fig.canvas.draw()
    from matplotlib.text import Text
    renderer=fig.canvas.get_renderer();W,H=fig.canvas.get_width_height()
    for artist in fig.findobj(Text):
        if not artist.get_visible() or not artist.get_text():continue
        box=artist.get_window_extent(renderer)
        assert box.x0>=-2 and box.y0>=-2 and box.x1<=W+2 and box.y1<=H+2,(name,artist.get_text(),tuple(box.bounds))
    for ext in ['pdf','svg','png']:fig.savefig(O/(name+'.'+ext),dpi=400)
    plt.close(fig)
def decorate(ax):
    ax.set_axisbelow(True);ax.grid(axis='y',color='#E5E8EA',linewidth=.45)
    ax.tick_params(direction='out',length=3)
def segments(xs,ys):
    run=[]
    for x,y in zip(xs,ys):
        if y is None:
            if run:yield run
            run=[]
        else:run.append((x,y))
    if run:yield run

# Discrete capacity response; gaps remain disconnected.
fig,aa=plt.subplots(2,1,figsize=(7.2,6.25),sharex=True)
fig.subplots_adjust(left=.155,right=.965,top=.945,bottom=.11,hspace=.38)
caps=[r['capacity'] for r in F['Figure1']]
for pol,col,marker,ls,name in [('S0',BLUE,'o','-','S0'),('S1',ORANGE,'s','--','S1')]:
    vals=[r[pol]['value'] for r in F['Figure1']]
    aa[0].plot(caps,[np.nan if v is None else v for v in vals],color=col,marker=marker,ms=4.3,lw=1.35,ls=ls,label=name,
               mfc='white' if pol=='S0' else col,mew=1.1)
aa[0].set(title='A  Coverage',ylabel='Assistance-gap group\nallocated care (%)',ylim=(0,108))
aa[0].legend(frameon=False,loc='upper left',fontsize=9,handlelength=2.4)
for pol,offset in [('S0',(-25,-19)),('S1',(-25,13))]:
    v=next(r[pol]['value'] for r in F['Figure1'] if r['capacity']==500)
    aa[0].annotate(f'{v:.1f}%',(500,v),xytext=offset,textcoords='offset points',color=BLUE if pol=='S0' else ORANGE,fontsize=9,fontweight='bold')
vals=[r['difference']['value'] for r in F['Figure1']]
for seg in segments(caps,vals):
    cc=[x for x,y in seg];vv=[y for x,y in seg]
    rr=[r['difference'] for r in F['Figure1'] if r['capacity'] in cc]
    aa[1].fill_between(cc,[p['lower'] for p in rr],[p['upper'] for p in rr],color=ORANGE,alpha=.16,linewidth=0)
    aa[1].plot(cc,vv,color=ORANGE,marker='o',ms=4.3,lw=1.35)
    aa[1].vlines(cc,[p['lower'] for p in rr],[p['upper'] for p in rr],color=ORANGE,lw=.7,alpha=.8)
aa[1].axhline(0,color='#7C858A',lw=.75)
aa[1].set(title='B  Allocation difference',ylabel='Additional gap allocations (S1 − S0)\n(per 1,000 candidates)',xlabel='Complete programmes per 1,000 original candidates',ylim=(-3,40),xticks=caps,xlim=(80,920))
for cap in [500]:
    r=next(r['difference'] for r in F['Figure1'] if r['capacity']==cap)
    aa[1].annotate(f"{r['value']:.2f}",(cap,r['value']),xytext=(8,-11),textcoords='offset points',color=DARK,fontsize=9)
for ax in aa:
    decorate(ax);ax.axvline(500,color='#B7BFC4',lw=.75,ls=(0,(3,3)),zorder=0)
save(fig,'Figure1')

# Tradeoff plane, with a true binned display of existing paired draws at 500 only.
hist=list(csv.DictReader((R/'data/display/JOINT_BOOTSTRAP_HISTOGRAM_500.csv').open(encoding='utf-8-sig')))
cmap=LinearSegmentedColormap.from_list('draws',['#F7F3ED','#D8C3A9','#A17E52'])
fig,axes=plt.subplots(1,2,figsize=(7.2,4.25),sharex=True,sharey=True)
fig.subplots_adjust(left=.105,right=.915,bottom=.21,top=.88,wspace=.15)
norm=Normalize(vmin=0,vmax=max(int(r['draw_count']) for r in hist))
for ax,mode,title in zip(axes,['known_equal','fixed_resource'],['A  Equal programmes','B  Fixed resources']):
    for r in hist:
        if r['mode']!=mode:continue
        x1,x2,y1,y2=[float(r[k]) for k in ['x_left','x_right','y_bottom','y_top']]
        ax.add_patch(Rectangle((x1,y1),x2-x1,y2-y1,facecolor=cmap(norm(int(r['draw_count']))),edgecolor='none',zorder=0))
    for r in F['Figure2']:
        if r['mode']!=mode or r['x']['value'] is None:continue
        cap=r['capacity'];x=r['x']['value'];y=r['y_loss']
        if cap==900:continue
        ax.plot(x,y,marker='o',ms=7 if cap==500 else 5.1,
                color=ORANGE if cap==500 else BLUE,mec=DARK if cap==500 else BLUE,mew=.8,zorder=5)
        label='800, 900' if cap==800 else str(cap)
        offset={300:(4,5),400:(4,-12),500:(6,2),600:(4,5),800:(6,7)}[cap]
        ax.annotate(label,(x,y),xytext=offset,textcoords='offset points',fontsize=9,fontweight='bold' if cap==500 else 'normal',zorder=6)
    ax.set(title=title,xlim=(-1,34),ylim=(-10,190),xticks=[0,10,20,30],yticks=[0,50,100,150])
    ax.axhline(0,color='#A4ADB2',lw=.55,zorder=1);ax.axvline(0,color='#A4ADB2',lw=.55,zorder=1)
axes[0].set_ylabel('Reduction in covered IADL need\n(index units per 1,000 original candidates)')
fig.supxlabel('Additional allocations to people with assistance gaps\n(per 1,000 original candidates)',x=.51,y=.075,fontsize=9.5)
cax=fig.add_axes([.943,.30,.015,.46]);cb=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax)
cb.ax.set_title('Resamples',fontsize=7.5,pad=7);cb.ax.tick_params(labelsize=7.5,length=2)
save(fig,'Figure2')

# Horizontal bar geometry throughout, contrasting hours and service reductions.
fig,axes=plt.subplots(2,1,figsize=(7.2,5.75),gridspec_kw={'height_ratios':[1,2.05]})
fig.subplots_adjust(left=.29,right=.94,bottom=.11,top=.92,hspace=.65)
ax=axes[0]
for i,r in enumerate(F['Figure3A']):
    p=r['point'];c=GRAY if r['process']=='universal' else ORANGE
    ax.barh(i,p['value'],height=.46,color=c)
    ax.errorbar(p['value'],i,xerr=[[max(0,p['value']-p['lower'])],[max(0,p['upper']-p['value'])]],fmt='none',ecolor=DARK,elinewidth=.7,capsize=2)
    ax.text(p['upper']+2.5,i,f"{p['value']:.2f} h",va='center',fontsize=9.5)
ax.set(yticks=[0,1],yticklabels=['Universal enquiry','Targeted enquiry'],xlim=(0,110),xticks=[0,25,50,75,100],xlabel='Additional nursing enquiry (h)')
ax.invert_yaxis();ax.set_title('A  Enquiry time',loc='left',pad=12)
ax=axes[1]
labs=['S0','S1: targeted','S1: universal','S0: rural travel','S1: rural travel']
for i,r in enumerate(F['Figure3B']):
    color=BLUE if r['policy']=='S0' else ORANGE
    ax.barh(i,r['reduction'],height=.49,color=color,alpha=1 if i<3 else .77,hatch='//' if i>=3 else None,edgecolor=DARK if i>=3 else color,lw=.35)
    if r['reduction']==0:ax.plot(0,i,'|',color=BLUE,ms=10,mew=1.5,clip_on=False)
    ax.errorbar(r['reduction'],i,xerr=[[max(0,r['reduction']-r['reduction_lower'])],[max(0,r['reduction_upper']-r['reduction'])]],fmt='none',ecolor=DARK,capsize=2,elinewidth=.7)
    ax.text(max(r['reduction']+2,r['reduction_upper']+1.5),i,f"{r['reduction']:.0f}",va='center',fontsize=9)
ax.set(yticks=range(5),yticklabels=labs,xlim=(0,90),xticks=[0,20,40,60,80],xlabel='Reduction from 500 complete programmes')
ax.invert_yaxis();ax.set_title('B  Programme shortfall',loc='left',pad=14)
for ax in axes:
    ax.set_axisbelow(True);ax.grid(axis='x',color='#E5E8EA',lw=.45);ax.tick_params(axis='y',length=0,pad=8)
save(fig,'Figure3')

# Source/follow-up flow using actual frozen partitions, never complement reconstruction.
fig,ax=plt.subplots(figsize=(7.2,7.6));fig.subplots_adjust(left=.03,right=.97,top=.96,bottom=.03);ax.axis('off')
def box(x,y,w,h,s,size=9.3,shade=False):
    ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,transform=ax.transAxes,facecolor='#EFF3F5' if shade else 'white',edgecolor='#6B7E8B',lw=.7))
    ax.text(x,y,s,ha='center',va='center',fontsize=size,transform=ax.transAxes)
def arrow(x1,y1,x2,y2):ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),transform=ax.transAxes,arrowstyle='-|>',mutation_scale=9,lw=.7,color='#6B7E8B'))
labels=['CHARLS 2018 interviewed','Age at least 60 years','Community dwelling','At least two reported conditions','Positive weight and cluster information','Qualifying functional measurements']
flow=F['FigureS1']['baseline']
seen=[]
for r in flow:
    if not seen or r['n']!=seen[-1]:seen.append(r['n'])
assert seen==[19752,10758,10699,6628,6283,2433]
for i,(label,n) in enumerate(zip(labels,seen)):
    y=.94-i*.105;box(.50,y,.62,.075,f'{label}\nn = {n:,}',shade=i==5)
    if i<5:arrow(.5,y-.038,.5,y-.065)
ax.text(.5,.335,'2020 status among the same 2,433 baseline participants',ha='center',va='center',fontsize=10,transform=ax.transAxes,fontweight='bold')
dd={r['category']:r for r in F['FigureS1']['followup']}
dest=[('eligible_2020','Observable eligible',.18,.245),('dead','Known death',.50,.245),('observed_function_not_eligible','Measured functional non-entry',.82,.245),('observed_noncommunity_not_eligible','Not community dwelling',.34,.11),('unresolved_current_qualification','Unresolved qualification',.68,.11)]
for key,label,x,y in dest:
    r=dd[key];box(x,y,.29,.085,f"{label}\nn = {r['n']:,}\n{r['mass']:.2f} per original 1,000",size=8.6,shade=key=='eligible_2020')
save(fig,'FigureS1')

# Conditional sampling stability from the already frozen grid only.
fig,axes=plt.subplots(1,2,figsize=(7.2,3.8),sharex=True,sharey=True)
fig.subplots_adjust(left=.115,right=.89,top=.87,bottom=.21,wspace=.16)
for ax,mode,title in zip(axes,['known_equal','fixed_resource'],['A  Equal 500 places','B  Fixed original resources']):
    rows=[r for r in F['FigureS2'] if r['mode']==mode]
    xx=sorted({float(r['min_gap_gain']) for r in rows}); yy=sorted({float(r['max_I_loss']) for r in rows})
    zz=np.full((len(yy),len(xx)),np.nan)
    for r in rows:zz[yy.index(float(r['max_I_loss'])),xx.index(float(r['min_gap_gain']))]=float(r['fraction'])
    assert np.isfinite(zz).all()
    im=ax.pcolormesh(np.r_[np.array(xx)-.5,xx[-1]+.5],np.r_[np.array(yy)-2.5,yy[-1]+2.5],zz,cmap='cividis',vmin=0,vmax=1,shading='flat',rasterized=False)
    ax.set(title=title,xticks=[0,5,10,15,20,25],yticks=[0,50,100,150,200],xlim=(-.5,25.5),ylim=(-2.5,202.5))
axes[0].set_ylabel('Maximum acceptable covered-IADL loss\n(index units per 1,000 original candidates)')
fig.supxlabel('Minimum required additional gap allocations per 1,000 original candidates',y=.075,fontsize=9)
cax=fig.add_axes([.92,.24,.018,.58]);cb=fig.colorbar(im,cax=cax);cb.ax.tick_params(labelsize=8);cb.set_label('Fraction of resamples',fontsize=8.2)
save(fig,'FigureS2')
print('Requested vector figures rendered; frozen values and intervals unchanged.')
