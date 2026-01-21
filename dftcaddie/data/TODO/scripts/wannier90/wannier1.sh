PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
FERMI=`grep Fermi results_nscf/*nscf.pwo | awk '{print $5}'`

for DIR in "$TMP_DIR" "$PREFIX/results_wannier90" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

rm -r $PREFIX/results_wannier90/*
cd $PREFIX/results_wannier90

KPOINTS=`kmesh.pl $WAN_GRID | tail -n +3`

cat > $NAME.win << EOF
!Omega is the spread of the WF
!Omega_I is the gause invariant term
!The Marzari Vanderbilt (MV) method minimizes the gauge dependant term

!The two main ingredientes are:
!M_mn: The overlaps between the cell periodic part of the Bloch states
!A_mn: (As starting guess) The projections of Bloch states into trial localized orbitals

exclude_bands   = 1-28,85-100
num_bands       = 56		!number of bands passed to the code

spinors			= true
num_wann        = 56		!number of WF
!select_projections = 1-52

num_iter        = 1000		!number of iterations of the minimization (default 100)
iprint			= 2
conv_tol 		= 1.0E-10
conv_window 	= 4
!restart         = default   !Restart from last .chk file
num_dump_cycles = 20        !Write data for restart every # cycles
dis_mix_ratio = 0.5         !Default of mixing ratio during disentaglement is 0.5

!dis_win_min     = $WIN_MIN		!top of the outer energy window
!dis_win_max     = $WIN_MAX		!top of the outer energy window
!dis_froz_min    = $FROZ_MIN		!Top of the inner (frozen) energy window
!dis_froz_max    = $FROZ_MAX		!Top of the inner (frozen) energy window
!dis_num_iter    =  50		!Number of iterations for the minimization of Omega_I
!dis_mix_ratio   = 1.0		!Mixing ratio for the Omeaga_I minimization

!fermi_energy = $FERMI		!for the .bxsf file that has the fermi surface
!fermi_surface_plot = .true.	!Whether to calculate the fermi surface
bands_plot = .true.			!Whether to calculate a bandstructure
use_ws_distance= .true.		!improves interpolation of the K-space Hamiltonian applying traslation to each WF
							!(suggested for write_hr=.true.)
write_hr= .true.			!Write Hamiltonian matrix in the WF basis
write_tb= .true.			!Lattice vectors, Hamiltonian and position operator matrices in the WF basis
write_xyz = .true.			!Atomic positions and final Wannier centres

!*****SYSTEM

BEGIN UNIT_CELL_CART		!cell lattice vectors
ang
$LATTICE
END UNIT_CELL_CART

BEGIN ATOMS_FRAC			!atomic positions
$ATOMIC_CRYST_POSITIONS
END ATOMS_FRAC

BEGIN PROJECTIONS			!set of localised functions used for initial guess
I:p
O:p
Nb:d
END PROJECTIONS

!*****KPOINTS

BEGIN KPOINT_PATH			!the path in the K-space, values in fractional coordinates
V   0.0 0.5 0.0     Y   -0.5 0.5 0.0
Y  -0.5 0.5 0.0     GM   0.0 0.0 0.0
GM  0.0 0.0 0.0     Y1   0.5 0.5 0.0
Y1  0.5 0.5 0.0     M1   0.5 0.5 0.5
M1  0.5 0.5 0.5     A    0.0 0.0 0.5
A   0.0 0.0 0.5     M   -0.5 0.5 0.5
M  -0.5 0.5 0.5     L    0.0 0.5 0.5
GM  0.0 0.0 0.0     A    0.0 0.0 0.5  
END KPOINT_PATH

mp_grid : $WAN_GRID				!Dimensions of the Monkhorst-Pack grid
BEGIN KPOINTS				!List of k-points of the Monkhorst-Pack grid
$KPOINTS
END KPOINTS
EOF

echo "Generating a list of the required overlaps (.nnkp file)..."
#Ekhi
wannier90.x -pp $NAME
#Planck
#srun --mpi=pmi2 wannier90.x -pp $NAME
echo "done"
