from __future__ import annotations
import base64
import hashlib
import zlib
from pathlib import Path

PAYLOAD_SHA256 = 'dce522f0f8762e7fd33586d263291c14b54ff4bd71a53ddb4667f9b73c7111c8'
PAYLOAD_B85 = r"""c-rke+j85ulJEWs9=}l9krYY3Byo+W%5jv5t1_`mb~07#xL6bk+8k4)4oNBYWc}~k-2e!H7m2bnr}km}kcecX(P;D?O$KQ)w;U%}=F5~hjup-qNt#=394EP(
he@36?8tjrE`NH-;!*y-bF;fBoXN|-vLu$jlT7}~ma|2gcq~(Q9<!YQCttWZj+ZlEz~#=)*U{MdI5~N59b2~N?(h3<Fx)#haA)3dZ|J+@nIEvj;Bfyn8~W_6
>ki)x4{REBc{)A2xN_coI)8_Q_q;c=*TEhOhGW-1@W=kX$A)jc@o?`DaJ?Swk6*Lb2kuZGjN?+a3fcEpE=!XviTW#+=Aq|CeON^hMy#K)I1BS|73Poq)wsV%
vfKk^E$0hlT0dKQxY#7^C#fICZnS^ccbEBHl7@d1Tl;*1{%w@Z0Bz>Ecxw^49-Ff`@2^JVR~*DK#tjyaNa~^UZhG?h^rKGdYLWdzq#X9g!|~zp?dX8d{eOu~
hwIt&$I01eB=pepU&DSMygob(*wA|eyZ`#&aKu0o4&1%q?Pxp<{82E2QTxut6o!n3dt<ziVhB($WbA^}9lU+Zm_PEp1GabY#vSjC-yX32@!o92W^V|?yOYa_
Go5_Efpa&E>E`Kla&mQc{+XWQli+~Oyu<xNcjmr5bp6rZ>w`W2;9%wk<Jr(VIPe0P%=3V#osW|#4nghcfVu*29j7};8E}2YI^CV=<m=hwPiK05j{AbpgN2&{
i?ZwS4av56qyY*D>y>4Lxb<gl#$cu$p9PlVrnf6+<wi@^2_pCQ$jb7xYxRG_|E>SAJ|{6d+Ogm-PapXY{0n2BJ-{TO+ylfgpc{mtOF-<wV~gDSiijs^nxtxM
%D@E0gqiMzfk5|*HL`v?wjvgHB;IcGFmWv*uL~SEa%mt#NsLnJWOr_7;XX!*>mONu=;d;S9Q`cuA7L>+?vJdM6(p&3--91vY>6?0FlY0u(?wG6t$&d^cr0Ax
mv`>?;Lv{J1i9Y<37W-$4|1P%5N*!_q0gOr_Lv=CrAr3a40glKlQcW-*gd;v*++J_XMz5pVRkbw439s!QO3Fh7JG@$I`%RT`fu#6zHDKP2N_Y&fw{YbJNDp*
w=By+Oau$Qr$D-cG&wNkJoGwfg^x(QdRCPsYP%6m$jxAW?}uqeh?!UhdkC}KN$%;Ala|jHzyKQfJ<RW%*qt+)Z-BpGYwQ7l*ah%_Q<t-cyrZ#AP}L);i1Xud
nTK6O^)0rMX~3W`zCAWrlw<>8Iyx{*k0>fQvS4Y3l!HM5?zjuMb^<qyfcYH|+9T^7Xvc)47tBkEDQt!M0*lnu#_spoN=yv`0{&FMm1S3;klM|Ggu1L+Ga1IP
9B=?4&}TvV0QqN25;)9&MuXVa(vdFX`nA9VyK8|G*h7xc%|ZGXc|EjvXpRs&h$>Y~ZD-yco4a3;{XpuGHR@^4AOu-vaMS*9a`p-A>E)MC=-SUdzjx5M|2aLm
xR^|BZAkvOU@!px!+q-x9FjN3(O~A_a@<=4163y|?cw4M&EOH5L?sDH>aZYS9(Xe5WXUr1m_8}@KrH>pTpxy(Id>=6U<_HtX9yd{c}MV^?1=b12s6;x5LDJ;
p!4#!hCp(dqtG^k&}i3XRN5mQo$fuSEI3V>n=_=4jE)BBhZ$&&ch?L7&OZlUF@MUkWt3;<3l`S`f>8riWoPj!xo-x@!yxp|d3<mZMTyriZ3aI1OAI@dX6%%L
jCwHinCaw!dCPnqRdgF3lgiQ4CtZrKOUC{Nm7vzOa0RWgxm+I$dt2Bd*equT0S_So6MkgP9&?tN&Z%nfN1d6C!z>#NAxbuSO!NSS$3P1?v%d`ypvg5vKxGOG
K-=GmVbl=@{)6|@72y4Az}~Zx*<Y~BH%2s&Ec2rp5YTweJo2Ip+#hKN`qIC{1x+(RJKnSCCq2wG110Qdn1wOe1lXJoAwj}$r{PvkDpm#JxOx=6D17(_acCaK
OQuhvjTPg}Dcsnvz{nXov|>=k9s~|a)Z;b?S<~&7rUouu7qlUFG(`I50-W5I)xMK0nCBpWvJN*v<RVpM7J*s6mV0$0qcg?;Ki&lwk}-W`SM10#23Kzmh9TEC
#fIUWxK;T0yBpni5bN6A!4W+rHyar5ySa<nQxQGdQz1F{$K?X!OO|(Vl#rB8x2qFFPe8Le_DZ;wu5}F2*=paW9pn){EJ)xJ_bAXW?wT|cmj>tzVxN<y?-M;$
3KTOZ2?C&T-9~|+h&>Xp$nzm*dJegF1lPl23lJ&Nrr{f83t$*N$Ux8;QYPXcMLI|H3lE+VRPjm7D%V7i#-ap3kr2$laDv4YORKD`M>NLC5mx~(i3B9wpmoFl
<rOz_tB9L8R_j+t0t6r6N~8l~oF2)zA-K5d5+rQS6O4`xk%Hix1^H))4h}U7r~vR7;()qkUyGUgkT`&~RLhb409l7*7xj`oEXdnAm_XI<cwx0keR185`m7cX
3#6xAOf5!h*BH<ugEaY@#URQSpoZkw58c}sGVajB8y+kI##nwD20+>mh5t!#fb{&B(<nu;m2LvHw&ViF$>0)glvW&kRMyPv3g`_ku$&*8`q#9ti<I>#o`q;1
7hXcm7i)LR*`mg8dIV-G%_)j)mU7{nxLk+}B^JfDaa1y2)%F$nrCnbWAT8bgVQ-e;#$ELjkSMgjd}d6s$OBtq%VY{d@`|#5Yz4cOJ%E7sM|lgLAeGt`y0LJ>
lws(uFX2ec`3qMPHN`L0l~NjibfdIjTvY=(O;rcREtFtAn<DsaxdE`G5E80*D5?dcP)5hKBA<;xD@t-t(A?RSS=wDM)@xQ!mSV+NaA+6}Q<QFDk_Qp2VZI~_
rJ2GdI-~_?r_xQK!vtWS9XilpGjs@Iv;)^Mk0Yu<L@DTsdC>4-8GE?G_blKsSIkQV=)^Iv3W4j)p?!8{Ktsgr8^ze#kR^yqQOLTW1s75mPpaTl1cq)DmC)7(
ICK+Wg>lsay=H0<eh>g7_*9=^{X|l6e-Qej=JaoyTqEcTJ%p?Re8#WVxGiN#?2C;CITq=yld)T@u$mUIz%LcSwhdJC>~?ERqgqVBkWPhs8^SiyS#H*GgJH%B
7)p$dO1~CjcY&z5>Sm~}y9kZUs7HvEWP2@$jxlAyCXBnhGF%T-BUW3)pxg>@<@b`gs4Q-XO~^i=;ag`j4AV?cTZboiU?-B4jt6KH6=5}z2}dm>6THIO7T%PR
3DAJo!XYCObP3FHL?pV=)UKf@<USQK^|9n2-6+M|rW<Sy#CP<XxK1oYm1d3mS8Iq$z%PDN@p_xscFih8+JH#)NGORokANzggcr#<TY-9vrH-kTiUdkv<ZOn~
MF*dVVv^8WUXq1D5*R`Q3ed$R2%2#{h(PKf@wcsSKvVZd1{v~P2QVq^4|acW{7)EOfm%1@c1Pdh-I_sEeBr*rh}5yVf*V;NtoZL{d|-1s%{Y%6Vksa}+bqk&
0veui(XP!x&Ump;^>ZW7pSMi3UiAZUEoD=PYiLA<wySLEXwhWOdRFjl_s0)p>vge5H&0KNVY|QWc7Je5d*U={+9jkBh}I;c9ERHV;IAZ<N+Ol1YPyP$a<d+R
Z~_4<)~7SWvMOcEbOjF~7I9(7cR`D)@5_k>WXn3c&l9=bE#h2Fl+1`$H)BQQsF~Pj5sge~O<fF94HSCI6pt<XC>U+2YKUXYdA1`eKh5DRT!^4h6m-<>`tsJA
oc!pSwJLyA#i+_=udh5-E0%m6G6JA0gJ=ACQLxEmfkFw249SGCspp=m=KiDA3e409QD2(ARz-@&4an+~v!9)tH5zbHVk+73Hl%><l&uOaDp|5+;+4=Y(oEpL
dk@AbjPpd)f%;k^Sw|tz)-ul%8COEl;dMbF=}mKexIwyAmQ~I2FgMzi=n>i*UF;Njt!0lQx=P?wAhH5MT8%Vnvpq=`7RNpYA2naQySpKD*?E4Hvh$w_NOmap
*l7`F?EL(QVsk*T+uZ>!^H5@d9TqZg;8Own`PN`BL8sU+Fd2Ac<3&rKIc^Ry>1>&^Of*`UC}36fI7Vx6aHGYjFql&)<3x1+uFlp@F0Z;~`N9c87WvvK8G@m~
;}7`YYC)swL~yE_R1#o0YUDg*;vH=yHnngC&GLEPC3^5)aWqnc5C0yKGOJqJkZUq<)T5|YK@>42lUfxv>N&$vc1jjVOp-muUghp-1irMm`sB`MzT15+F`P}*
`B;_+q^xTUVo~FvWIaD>!T+hXHm-Bc8b#DXL+02<Py}ZAauKm>Iy^G|xhaKf1;&gH#H#p(dB$+S)GD3`!yr2Lq2qCd3{%umRi&y$sKNrMu_9wxV+PQgX~w9w
9@L1K>g#QhgPGb`ND9*oQ|!tDDv%iy#lc#VD&S&6WrW(HiHZ{wex>R&7^|5Oe7f?bIl_SH8u6!?{)JJ1mZ!`B;=U9Eh)MpHKG|#1&idq`DW+3dr|yll-1E*|
F!1rnS2v}Szby34QVjIN+n6@zXQo3%G*=%PwmknoA>z8SKusYY?|Z52Q>{rU`r7o7vIJPQc(SENmCRAIMB`iNQ&2H|H?`ZG1q^CiK-QfKG&h^9+x-9=n=GKp
Qah>YkNO#2eIi(%e@#x9g7QEJ1w!h2*y}j1w6%3eVz@1)Q+;1GliV?C-c!B&gLD}y19@%VhB-!+{ZpHG(2;G&-5&MG^+}2l0$VNY8`X1#5_PN^t$0kmpjQ%-
WxiNe9^NtU{#a|=DpV0^9PqVc%M*$iRaWVKmivHiz-x~@1r+ZYY_JycWPLQ2Nfc3lT?EoDXcK^KP}eL?m90RIW8104XQr0ySC)G7Kx-J5ps*MhLS<|K>u@C0
<8@qZ6DxQ?0Ag|4>kwP7k?_d%;e}j=cz%qe4t!SaMh2msqf~>SK}vsY?c)C(v}j?(NGv8FK1@!p&c05Z%kwYO(+L+C>{~}+L2&GT=57D5aP4Pzw>WAiGDPjl
n6ho1N?WrWZxtG05%HkncOXA{IuF8{g8n3FaSoswi*+hsA(+>Hn4bUl<g-(^Y9R;Z+n^#N!D%m9AftcSvgu!Rtx8VG_EtQ=ckmSuuGOU9ve>f>BM?JJ^rIVF
Q7omN|1`b$j}ru%zv6uWc#r368y0EyKx>AR<KpI0+EspU^UlGhM?Q@ZHqD|n3uCJ7tJ+S{w`-Wkf&^Smab}JTqfYQ`tfPSn^|Ot!HR~%*2If99nd_`xJ8+Rw
W)6Z?0+uH_DeN$0>-88$Ba+8u?#@7jOjvVw@K_dsI;Clf{V4!UEG>eZFur5h0_)>`FFjyCY!ompL8BdE|Gl-0-IW^>e!E*+;^DIi$?1}skGE2Djg?xx2eH=F
qGt>OBIaNv8hL6ixe#A^d4@Ng#DI61-)YS!eGe0=qGy9Q<Qr?#Cwaz#ibcGl24f5H)EE10UVc%uIh^~)RPm*w?Y7#d_7Z5Hg}x8OK<YAogePGh0!h4)To%Z*
gPX?2IkBe|_=dA=vsb89wY#>xs4Q9qP}{xW10W#4q|)CgV79r!CgGCLUo2kcM9*AQvyjOhR%Z5CohnJMXqVn>v?(4m-r}>n3VJ%Z_;hkQ`D60=3LOeUo3{?7
Bi1G@ek(j;rV@66QDMPG0)<GCznM#Oh76)?EyT0bFn@%IJs>aUFFiagOau=#H7qj&6;Ba>tuSQ<7!WTYD~wTrB9?391iSJT$sh6%;>q6Su6nCkx&Osf);#x<
b>w*nf=b5@?d{PP)7P0F%%YTm;>~{sN9--EM?uS4^P!+x+j5Fnw(?6fq{(s=6mZdhf$7ku*={i{eNsA0$-tLt7*$3iAk2TQ-g~}j(+*9vcy5}8`o0_I8j#ok
a-N{^x7wC|n452?ac2v9C|>W9Ib*K|<kExGGXFiy-$A-^dFPG<yq1R54V%a%Uy{s;SBj3xuXA!2S$_Z1c#TKHj;eSmPYeIRla!<4oUuy8{zZz<@zsc$hjQur
4J+Tr<ESYMIE;Mzxd!f3oH41s<MP3jHfXg!F;Bbby<vPIu(2ON36JqY8qkJ9c&@bUtCZ0{QA96L$N}#)7R5Sg@|~Z1V50|`FfBy8(eZ*Jal{uX`vl_jO#G&g
)@L9YekN8;eRY&c4Yo@_c1rI2Xp>dbFqsCVph!ogn~?IdPPt~jOEJX;cu+(<k5f>}7IXQ!<gZ9G|3jM0KLIsDsLk4tG3>Mm7(ZdL_asBb^zJXv(Nsr%ze^&a
g1@sEjH-9}80YQ-P)ctfg8BH8)xI;R&nZmNAKc%a!&W8n?K^IDKDfCXRVRipKyYKq&_01UfkRr+R3%XHX76N$2F+vdL2fXAf0T-~X6Wkm1by_?_e7H@-1^^v
scXiOYdteOYXci<B;s<p0QJl2;mJ3hq<I)1UG75?C-cX5Y2x|~Z;USE`#AX?%OR5o#=j(S0v^700x8(I#3_s1hgvYSAnPH78)*c3(yI!Z3nqV3G%?AJ2C!ap
mb=&#(pmSmJ@`KPtpQ5q<K=wD(xQ9iV%k1c+{g2BKHhM`qNr<3gZFH`mxc~TN<j3vh*HB16+N{>e@^Dc0&A5}qN<d?mOBcb)xo1?X>5FGoR;?`@M)!s+h#_>
4oJ!~7;L4JHa-oS>e$|rb2NVK41Vh3GkL^-%D&AU?{T;ar`F9hXX!1TR>`SIU$&WxBdAU$^od6Rg(?*vY%o-+XGQLeMKulY#-~fxDyQ-B5}jbn&G2^Rb0qS^
0y}FX)R^76l=KDR10Hr*%UA|A(Ic=DttPe|A^lHk*_0+}i&bCl*!ZQ2mwti)<HrloxYMgIC!d^;XO~y!)3a0fDOKWfa&a={3VAU-KmYJkzs>OfA1V0Hf23fc
e-cKWJ1=7)hDjVfb_xyDg)v#?+I2|~4c$v-JoJ#?$-${I6DdCiqi@1gzV6c9pu`frf-5^{dh2CP)qh9zk#J4T^sgL<Gjy%_*W>;YKa)1_8C&3w8Zr><nmf{)
Yw~J0mg)tq%z15p$58TP;kfi<ibs~T!A)inr|Vf9NuB$%xJ!TDDkx^qR$&iq>%Xl1VbdyjPPr}B=(j02c^RwGlM|8PmHPbqTn%K3ymnhUrK^7~p*#v861^zF
;JJywON88(JP~9(k2c}eaW*tNHH2}9GvT${6IXKg&n1utI5;7h#~K2`08$vUJ&E{cgBbzYnsvY~Z17&S<!JMJ5^dkW-tDy-rz*E5yynV{hU|jS<GLE_+Fm6w
Qid$*Al8krzFKWQFPjy^^tUd*ig`5~-Xa<^cfDwxKjrmlEFXO0Xq5mMksI&9%v!Rh(wg5dTJv>|)dYFE42e4VPn4maRgwz*OH}Kmq#$K$DUl<~&2?3&N!dJE
=`SU`OiaYYFA)=gLb+L^cJo3R*~FL)!g0&XQVve&#7USLw#NF!+Wi*8#!*i9E#{G6mVJxGi-YQhdK0h}TdVVSYs~60PFaM3uc)3)0QxfmpWVhu3S#<5RXARK
EBuGDo(at?x&uT*<z_vwH@uHf683d3xyhiVtre{&czc_glp8)J%0@FQ-mshT;^~WxYu!R#qC<pG6<;qU=J$yBrzp}Ip7CvHsZn(q@usY}lo?-~TwcB?GZr=A
!<NTDN*~&t1WEK)AS_vsr1KNZc>pivJ|#FARDInCfFIRQFf8zxNCKHv$zB!uj-MNK%mI3Rv8$EzY7oqdbEOgvz5LkK>T@+Xyvmu=W?W75@W{E$0TEBv!1GwN
3@=J>HSi+1E)S5EG;_pLY44=|!EpJr1kt*J(yofKRVAfWHD&9H$`)0XR+W|Y)fH7?c|nz>q0%DjC0eybGrmSuuVQ^mH9>{Su&!iFRWJCzmm!{Nf>Xu8W+Aa~
U`5#!>mB7HqE@YGSEQ+{c7qY+<?d(N(ai;A{7M){C>jn$JsKx$C|#R7O7t~s=`*I!SQPZpsF&J`MZR?WJcD1mjz+K26<<uDDYsw4tAeJ!=mx+1c(VRrL)WP-
Pamor<jAZUe)YypAL~9LAZ8cxj#Zvc^?1$h)A#KOYaeTw)ORGm9<C_EdO-cBj#vAASuD`vFx0?$a5dX9H@^XZ{3zxT{k8&6+ppotRaip1Gs_^5-iB$Wp<LFb
?@>#Nx;_4VYC%!A{87D~YF&5hGHa3M$Y%d*YA(N;o_xOia6bLRIr;Mb?1~I5KUgg+F%d0Ztw=J^lU104Z7TZH!K9G2a4t@+K4Sl0mGufoD{h-8QJw|Qecps2
z6ovd&TI93InL;^@g>$O3c8vJ*5h!!bzd>J^{W%xIF$7tM6Ws(d=E~X=kWLU9aK4dGeNxUiTbzmzr|Uep8""".replace('\n', '')
raw = zlib.decompress(base64.b85decode(PAYLOAD_B85.encode('ascii')))
if hashlib.sha256(raw).hexdigest() != PAYLOAD_SHA256:
    raise RuntimeError('V16 payload SHA-256 drift')
exec(compile(raw, str(Path(__file__).resolve()), 'exec'), globals(), globals())
