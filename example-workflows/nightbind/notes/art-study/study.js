import * as THREE from 'three';

// Bounded concept study: one keeper/lantern and one environment kit treatment.
// Other creatures are authored 2D silhouette proposals for the independent modeler.
const shapes={
 ember:['Emberling','#e69a55','kiln pear · forked flame','M-20 40 Q-49 7 -29 -17 L-18 -40 -5 -25 8 -55 19 -26 Q43 -3 28 30 L36 46 10 40 0 46 -10 40 Z'],
 thorn:['Thornback','#9dab72','broad shield · three blunt thorns','M-50 24 -56 -8 -42 -25 -40 -40 -29 -40 -27 -22 -8 -27 -6 -45 7 -45 10 -27 29 -23 32 -40 43 -40 45 -23 57 -3 52 27 36 31 36 44 19 44 15 30 -15 30 -19 44 -38 44 -38 27 Z'],
 volt:['Voltwing','#75bfd7','broken chevron · forked tail','M0 -20 -15 -13 -53 -43 -43 0 -25 -10 -13 17 -3 19 -12 48 0 35 12 48 3 19 13 17 25 -10 43 0 53 -43 15 -13 Z'],
 mire:['Mireling','#ac8cbb','low crescent · three spouts','M-48 29 Q-55 4 -26 0 L-27 -32 -13 -40 -2 -28 -8 -7 10 -10 9 -45 25 -49 34 -34 26 -10 35 0 44 -22 55 -19 53 8 Q60 32 33 37 L47 48 -11 46 Q-42 49 -48 29 Z'],
 fang:['Fangling','#c48371','long jaw · lean four-leg stance','M-54 -10 -38 -30 -14 -26 4 -12 29 -23 41 -44 47 -20 59 -3 42 12 30 9 39 48 26 48 10 19 -12 18 -25 45 -37 43 -31 10 -43 6 Z'],
 moth:['Mourning Moth','#d4c58d','four round veils · narrow body','M-5 -16 Q-48 -65 -57 -25 Q-62 5 -19 9 Q-51 25 -38 47 Q-10 57 -3 18 L0 40 4 18 Q14 57 41 44 Q51 22 19 8 Q60 7 56 -26 Q47 -64 5 -16 L0 -32 Z'],
 pyre:['Pyre Warden','#e1af6b','upright furnace · shield shoulders','M-39 14 -52 -2 -45 -28 -24 -25 -25 -42 -11 -34 0 -56 12 -35 29 -45 25 -24 44 -28 53 -3 37 15 27 10 25 36 38 48 8 48 0 27 -9 48 -38 48 -25 35 -28 10 Z M-10 -14 -16 16 16 16 11 -14 Z'],
 storm:['Storm Serpent','#78c3d3','S ribbon · forked frill','M-48 -35 -27 -22 -14 -49 3 -26 28 -39 42 -24 24 -8 3 -3 Q-34 2 -14 20 Q15 41 49 21 L42 47 Q-10 65 -39 28 Q-61 -12 -11 -21 Z'],
 dusk:['Dusk Reaper','#c4ada9','reared jackal · split veil','M-9 -22 -17 -47 -4 -37 7 -55 14 -31 33 -18 21 -5 8 -3 10 15 50 45 8 36 2 17 -9 45 -52 47 -23 18 -20 0 -45 -3 -55 -23 -34 -12 Z'],
 solar:['Solar Seraph','#f2d494','open sunwheel · six swept feathers','M-17 -21 -5 -39 7 -20 18 -44 27 -23 60 -35 45 -3 28 -7 62 17 34 27 48 49 13 35 2 51 -10 34 -45 50 -33 26 -63 16 -28 -7 -46 -2 -61 -35 -29 -25 -20 -47 Z M-12 -8 -17 13 -1 26 16 12 11 -9 Z'],
 world:['Worldcoil','#80c7ac','closed serpent ring · thorn crown','M-12 -44 5 -29 28 -49 33 -26 Q68 -11 52 29 Q41 56 -5 49 Q-59 47 -59 8 Q-58 -22 -26 -29 Z M-22 -7 Q-47 12 -20 26 Q17 43 31 17 Q37 -4 11 -11 L0 1 Z'],
 eclipse:['Eclipse Sovereign','#d5b7dc','crescent predator · hollow moon','M25 -50 Q-38 -52 -52 -7 Q-66 35 -24 51 L-39 25 -12 34 -5 54 9 32 34 41 19 15 51 7 31 -1 43 -18 25 -29 14 -7 Q-18 4 -20 -15 Q-18 -35 25 -50 Z'],
 boss:['The Bellkeeper','#ad95b2','hollow bronze bell · hanging clapper','M-19 -42 -12 -56 10 -56 20 -42 35 -33 41 6 62 31 48 42 29 36 23 51 9 50 7 23 -7 23 -10 50 -24 51 -31 36 -47 42 -62 31 -41 7 -35 -33 Z M-15 -26 -23 17 23 17 15 -26 Z'],
};
const svg=(id,black=false)=>{const [name,color,role,path]=shapes[id];return `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="130" viewBox="-70 -65 140 130"><path d="${path}" fill="${black?'#263c40':color}" fill-rule="evenodd"/><path d="M-9 -8h6v5h-6z M5 -8h6v5H5z" fill="#152931"/></svg>`;};
const plate=document.querySelector('#plate');
plate.innerHTML='<div style="font:30px Georgia">The horde becomes a lineage.</div><p>Primary forms first. These are flat silhouette proposals; preserve their negative spaces and proportions when modeling in three dimensions.</p>'+[['FIRE / PROTECTION',['ember','thorn','pyre','solar']],['STORM / CONTROL',['volt','mire','storm','world']],['VEIL / HUNT',['fang','moth','dusk','eclipse']]].map(([n,ids])=>`<div class="family-name">${n}</div><div class="family">${ids.map(id=>`<article class="card">${svg(id,true)}<strong>${shapes[id][0]}</strong><small>${shapes[id][2]}</small></article>`).join('')}</div>`).join('');
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(1);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.3;document.querySelector('#world').append(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color(0x101c23);scene.fog=new THREE.FogExp2(0x101c23,.014);
const camera=new THREE.OrthographicCamera(-32,32,18,-18,.1,110);camera.position.set(0,36,28);camera.lookAt(0,0,0);
scene.add(new THREE.HemisphereLight(0xc4e5ed,0x3f3c37,2));for(const [c,i,p] of [[0xffdba5,3,[-14,24,9]],[0x729fdb,2,[10,12,-18]]]){const l=new THREE.DirectionalLight(c,i);l.position.set(...p);scene.add(l);}
const mat=c=>new THREE.MeshStandardMaterial({color:c,roughness:.88,metalness:.06});
const materials={ink:mat(0x1c343d),bone:mat(0xd9d3b8),teal:mat(0x3f696b),brass:mat(0x9b7852),slate:mat(0x283e42),stone:mat(0x435c5d),light:new THREE.MeshBasicMaterial({color:0xf1cf82})};
const mesh=(g,m,p,parent=scene)=>{const o=new THREE.Mesh(g,materials[m]);o.position.set(...p);parent.add(o);return o;};
const keeper=new THREE.Group();scene.add(keeper);
// Split mantle around a dark central leg gap; broad shoulder cap and negative hood.
for(const s of [-1,1]){const coat=mesh(new THREE.ConeGeometry(.32,1.12,4),'bone',[s*.23,.7,0],keeper);coat.rotation.y=Math.PI/4;coat.rotation.z=s*.08;mesh(new THREE.BoxGeometry(.17,.4,.22),'ink',[s*.19,.19,.03],keeper);}
const shoulders=mesh(new THREE.SphereGeometry(.5,8,4),'bone',[0,1.08,0],keeper);shoulders.scale.set(1,.36,.65);
const hood=mesh(new THREE.SphereGeometry(.31,8,6),'teal',[0,1.47,0],keeper);hood.scale.z=.9;
mesh(new THREE.BoxGeometry(.35,.27,.08),'ink',[0,1.42,.255],keeper);
mesh(new THREE.BoxGeometry(.15,.12,.1),'light',[0,1.35,.29],keeper);
const arm=mesh(new THREE.BoxGeometry(.15,.65,.16),'teal',[.55,.95,0],keeper);arm.rotation.z=.5;
const lantern=new THREE.Group();lantern.position.set(.78,.76,.12);keeper.add(lantern);
mesh(new THREE.CylinderGeometry(.23,.23,.1,6),'brass',[0,.3,0],lantern);mesh(new THREE.CylinderGeometry(.27,.23,.1,6),'brass',[0,-.2,0],lantern);mesh(new THREE.OctahedronGeometry(.19),'light',[0,.05,0],lantern);
for(let i=0;i<4;i++){const a=i*Math.PI/2;mesh(new THREE.BoxGeometry(.05,.46,.05),'brass',[Math.cos(a)*.21,.05,Math.sin(a)*.21],lantern);}const handle=mesh(new THREE.TorusGeometry(.14,.025,4,10),'brass',[0,.47,0],lantern);
mesh(new THREE.CylinderGeometry(20.2,21,.8,80),'slate',[0,-.46,0]);
for(const r of [7.8,14.6,19.7]){const ring=mesh(new THREE.TorusGeometry(r,.035,3,96),'brass',[0,-.015,0]);ring.rotation.x=Math.PI/2;}
for(let i=0;i<24;i++){const a=i*Math.PI/12;const step=mesh(new THREE.BoxGeometry(2,.22,1),'stone',[Math.sin(a)*20.5,-.1,Math.cos(a)*20.5]);step.rotation.y=a;}
const arch=new THREE.Group();arch.position.set(18.5,0,-12);arch.rotation.y=Math.atan2(-18.5,12);scene.add(arch);
for(const x of [-2.5,2.5]){mesh(new THREE.BoxGeometry(1.1,4,1.4),'stone',[x,1.8,0],arch);mesh(new THREE.BoxGeometry(1.5,.5,1.7),'ink',[x,.1,0],arch);mesh(new THREE.BoxGeometry(1.3,.3,1.5),'brass',[x,3.6,0],arch);}
const span=mesh(new THREE.TorusGeometry(2.5,.55,4,10,Math.PI*.86),'stone',[0,3.2,0],arch);span.rotation.z=Math.PI*.07;
const bell=mesh(new THREE.ConeGeometry(.8,1.1,8,1,true),'brass',[0,3.2,0],arch);bell.rotation.x=Math.PI;mesh(new THREE.SphereGeometry(.17,6,4),'ink',[0,2.6,0],arch);
for(const [x,z] of [[-21,0],[21,0],[0,22]]){const shrine=new THREE.Group();shrine.position.set(x,0,z);scene.add(shrine);mesh(new THREE.BoxGeometry(1.2,.8,1.2),'ink',[0,.3,0],shrine);mesh(new THREE.ConeGeometry(.7,2.3,5),'stone',[0,1.6,0],shrine);mesh(new THREE.OctahedronGeometry(.28),'light',[0,2.7,0],shrine);}
// Existing ground warning language is retained under the study silhouettes.
for(const [x,z,r,c] of [[3,3,2.3,0x9c78d0],[-5,1,2.3,0xe0b79c],[7,-5,5,0xe0b79c]]){const ring=new THREE.Mesh(new THREE.RingGeometry(r*.85,r,48),new THREE.MeshBasicMaterial({color:c,side:THREE.DoubleSide}));ring.rotation.x=-Math.PI/2;ring.position.set(x,.025,z);scene.add(ring);}
keeper.scale.setScalar(1.18);
const crowd=new THREE.Group();scene.add(crowd);const width={ember:1.05,thorn:1.4,volt:1.8,mire:1.35,fang:1.45,moth:1.7};
const tight={ember:'-46 -58 90 108',thorn:'-58 -48 116 96',volt:'-56 -46 112 98',mire:'-57 -52 117 106',fang:'-57 -47 118 99',moth:'-62 -55 124 112'};
const projectedHeight={ember:1.55,thorn:1.55,volt:1.35,mire:1.35,fang:1.65,moth:1.5};
const textureLoader=new THREE.TextureLoader();for(const [i,id] of ['ember','thorn','volt','mire','fang','moth'].entries()){const texture=await textureLoader.loadAsync('data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg(id).replace('-70 -65 140 130',tight[id])));texture.colorSpace=THREE.SRGBColorSpace;const material=new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false});for(let j=0;j<15;j++){const a=(j*6+i)*2.399963,r=5+((j*13+i*7)%130)/10;const o=new THREE.Mesh(new THREE.PlaneGeometry(width[id],projectedHeight[id]),material);o.position.set(Math.cos(a)*r,.7,Math.sin(a)*r);o.quaternion.copy(camera.quaternion);crowd.add(o);}}
crowd.visible=false;
let mode='camera',busy=false;
const buttons=['camera','detail','busy','silhouettes'];
function draw(){const detail=mode==='detail';const h=detail?3.3:18;camera.left=-h*innerWidth/innerHeight;camera.right=-camera.left;camera.top=h;camera.bottom=-h;camera.position.set(0,36,28);camera.lookAt(0,detail?.65:0,0);camera.updateProjectionMatrix();renderer.render(scene,camera);document.querySelector('#study-observation').textContent=JSON.stringify({kind:'authored concept study',core:'core-220cfa39951c',viewport:[innerWidth,innerHeight],halfHeight:h,worldPixelsPerUnit:innerHeight/(h*2),keeperBounds:new THREE.Box3().setFromObject(keeper).getSize(new THREE.Vector3()).toArray(),crowd:busy?90:0,mode,limitations:'Only keeper and environment are 3D concepts; crowded bases are 2D silhouette billboards, requiring actual GLB runtime inspection later.'});}
for(const id of buttons)document.querySelector('#'+id).onclick=()=>{if(id==='busy'){busy=!busy;crowd.visible=busy;mode='camera';}else mode=id;plate.style.display=mode==='silhouettes'?'block':'none';document.querySelector('.caption').style.display=mode==='silhouettes'?'none':'block';document.querySelector('.legend').style.display=mode==='silhouettes'?'none':'flex';for(const x of buttons)document.querySelector('#'+x).setAttribute('aria-pressed',String(x==='busy'?busy:x===mode));draw();};
addEventListener('resize',()=>{renderer.setSize(innerWidth,innerHeight);draw();});draw();
