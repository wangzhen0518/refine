alpha=0.3
beta=0.5
gamma=0.2
benchmark=adaptec3
mkdir -p results/${benchmark}
python mixedmask.py --seed 2027 --iter_rounds 20 --front dreamplace-mixed --dataset ${benchmark} --alpha ${alpha} --beta ${beta} --gamma ${gamma}
python dreamplace/Placer.py --type refine --method dreamplace-mixed --config test/ispd2005/${benchmark}.json | tee results/${benchmark}/result.log
python draw_placement.py
cp -r results/${benchmark} results/${benchmark}_${alpha}_${beta}_${gamma}
