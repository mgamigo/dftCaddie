PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
HR_FILE=`ls results_wannier90 | grep hr.dat`
FERMI=`grep Fermi results_nscf/*nscf.pwo | awk '{print $5}'`

for DIR in "$PREFIX/results_wantools" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

rm -r $PREFIX/results_wantools/*
cd $PREFIX/results_wantools

cat > wt.in << EOF
&TB_FILE
Hrfile = '../results_wannier90/$HR_FILE'
Package = 'QE'             ! obtained from VASP, it could be 'VASP', 'QE', 'Wien2k', 'OpenMx'
/

LATTICE			   ! crystal lattice information
Angstrom
   7.592002521   -1.962002321    0.000000000
   0.000000000   -3.924004641    0.000000000
  -2.009631121    0.000000000    7.246501605

ATOM_POSITIONS
8                               ! number of atoms for projectors
Direct                          ! Direct or Cartisen coordinate
Nb    0.498642747    0.714496784    0.710140545
Nb    0.501357253    0.713139532    0.289859455
O     0.498293251    0.246884777    0.714645434
O     0.501706749    0.245178028    0.285354566
I     0.188199370    0.908882265    0.413263963
I     0.811800630    0.597081636    0.586736037
I     0.239099463    0.886618758    0.930889844
I     0.760900537    0.625718221    0.069110156

PROJECTORS
 5 5 3 3 3 3 3 3
Nb dz2 dxz dyz dx2-y2 dxy
Nb dz2 dxz dyz dx2-y2 dxy
O px py pz
O px py pz
I px py pz
I px py pz
I px py pz
I px py pz

&CONTROL
!> bulk band structure calculation flag
BulkBand_calc         = T
FindNodes_calc        = F
BulkFS_calc           = F
BulkFS_plane_calc     = F
BulkGap_cube_calc     = F
BulkGap_plane_calc    = F
SlabBand_calc         = T
WireBand_calc         = F
SlabSS_calc           = T
SlabArc_calc          = F
SlabSpintexture_calc  = F
Wanniercenter_calc    = F
MirrorChern_calc      = F
BerryPhase_calc       = F
BerryCurvature_calc   = F
EffectiveMass_calc    = F
Translate_to_WS_calc  = F
WeylChirality_calc    = F
AHC_calc= F
/

&SYSTEM
NSLAB = 10 
NumOccupied = 38   		! NumOccupied
SOC = 1                 ! soc
E_FERMI = $FERMI        ! e-fermi
Bx= 0, By= 0, Bz= 0     ! Bx By Bz
surf_onsite= 0.00        ! surf_onsite
/

&PARAMETERS
OmegaNum =  2000      ! omega number       
OmegaMin =-5 ! 0.2 ! -0.65    ! energy interval
OmegaMax = 1.5 ! 0.2    ! energy interval
Nk1 = 100         ! number k points 
Nk2 = 100         ! number k points 
Nk3 = 50        ! number k points 
NP = 2              ! number of principle layers
Gap_threshold = 0.000001 ! threshold for GapCube output
/

KPATH_BULK            ! k point path
8              ! number of k line only for bulk band
V   0.0 0.5 0.0     Y   -0.5 0.5 0.0
Y  -0.5 0.5 0.0     GM   0.0 0.0 0.0
GM  0.0 0.0 0.0     Y1   0.5 0.5 0.0
Y1  0.5 0.5 0.0     M1   0.5 0.5 0.5
M1  0.5 0.5 0.5     A    0.0 0.0 0.5
A   0.0 0.0 0.5     M   -0.5 0.5 0.5
M  -0.5 0.5 0.5     L    0.0 0.5 0.5
GM  0.0 0.0 0.0     A    0.0 0.0 0.5  

MILLER_INDICES
1 0 0

!SURFACE
!-1 1 0
!1 1 -1
!0 0 1

KPATH_SLAB
4        ! numker of k line for 2D case
X 0.5 0.0 G 0 0 
G 0.0 0.0 Y 0.0 0.5
Y 0.0 0.5 M 0.5 0.5
M 0.5 0.5 X 0.5 0.0
EOF

echo "running wannier tools..."
mpirun -np $NPROCS wt.x
echo "done"
