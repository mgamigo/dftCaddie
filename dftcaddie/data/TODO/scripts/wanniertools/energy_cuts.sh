PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
HR_FILE=`ls ../../results_wannier90 | grep hr.dat`
FERMI=`grep Fermi ../../results_nscf/*nscf.pwo | awk '{print $5}'`
ENERGY=`pwd | rev | cut -d\/ -f1 | rev | tr n -`

for DIR in "$PREFIX/results_wantools" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

rm -r $PREFIX/results_wantools/*
cd $PREFIX/results_wantools

cat > wt.in << EOF
&TB_FILE
Hrfile = '../../../results_wannier90/$HR_FILE'
Package = 'QE'             ! obtained from VASP, it could be 'VASP', 'QE', 'Wien2k', 'OpenMx'
/

LATTICE			   ! crystal lattice information
Angstrom
   4.998029453  -0.000000000  -0.000000000
  -2.499014732   4.328420480  -0.000000000
  -0.000000000  -0.000000000   6.820731213

ATOM_POSITIONS
9                               ! number of atoms for projectors
Direct                          ! Direct or Cartisen coordinate
Nb            0.5000000000        0.5000000000        0.8333333300
Nb            0.5000000000        0.0000000000        0.5000000000
Nb            0.0000000000        0.5000000000        0.1666666700
Ge            0.6716652770        0.8358326385        0.1666666700
Ge            0.8358326385        0.6716652770        0.5000000000
Ge            0.8358326385        0.1641673615        0.8333333300
Ge            0.3283347230        0.1641673615        0.1666666700
Ge            0.1641673615        0.3283347230        0.5000000000
Ge            0.1641673615        0.8358326385        0.8333333300

Ge:p
Nb:d
PROJECTORS
 5 5 5 3 3 3 3 3 3
Nb dz2 dxz dyz dx2-y2 dxy
Nb dz2 dxz dyz dx2-y2 dxy
Nb dz2 dxz dyz dx2-y2 dxy
Ge px py pz
Ge px py pz
Ge px py pz
Ge px py pz
Ge px py pz
Ge px py pz

&CONTROL
!> bulk band structure calculation flag
BulkBand_calc         = T
FindNodes_calc        = F
BulkFS_calc           = F
BulkFS_plane_calc     = F
BulkGap_cube_calc     = F
BulkGap_plane_calc    = F
SlabBand_calc         = F
WireBand_calc         = F
SlabSS_calc           = F
SlabArc_calc          = T
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
OmegaNum =  1000      ! omega number       
OmegaMin =-2.5 ! 0.2 ! -0.65    ! energy interval
OmegaMax = 3.5 ! 0.2    ! energy interval
Nk1 = 500         ! number k points 
Nk2 = 500         ! number k points 
Nk3 = 50        ! number k points 
NP = 2              ! number of principle layers
Eta_arc = 0.00001  !infinite small value, like broadening
E_arc = $ENERGY
Gap_threshold = 0.000001 ! threshold for GapCube output
/

KPATH_BULK            ! k point path
9              ! number of k line only for bulk band
G   0.000   0.000   0.000    M   0.500   0.000   0.000
M   0.500   0.000   0.000    K   0.33333333  0.33333333  0.000
K   0.33333333  0.33333333  0.000    G   0.000   0.000   0.000
G   0.000   0.000   0.000    A   0.000   0.000   0.500
A   0.000   0.000   0.500    L   0.500   0.000   0.500
L   0.500   0.000   0.500    H   0.33333333  0.33333333  0.500
H   0.33333333  0.33333333  0.500    A   0.000   0.000   0.500
L   0.500   0.000   0.500    M   0.500   0.000   0.000
K   0.33333333  0.33333333  0.000    H   0.33333333  0.33333333  0.500


!MILLER_INDICES
!1 0 0

SURFACE
0 1 0
0 0 1

KPATH_SLAB
4        ! numker of k line for 2D case
X 0.0 0.5 G 0 0 
G 0.0 0.0 Y 0.5 0.0
Y 0.5 0.0 M 0.5 0.5
M 0.5 0.5 X 0.0 0.5

KPLANE_SLAB
-0.5 -0.5      ! Original point for 2D k plane
1.0  0.0      ! The first vector to define 2D k plane
0.0  1.0      ! The second vector to define 2D k plane  for arc plots
EOF

echo "running wannier tools..."
mpirun -np 6 wt.x
echo "done"
