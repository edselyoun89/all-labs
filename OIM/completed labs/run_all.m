%% Запуск всех четырёх лабораторных. Требуется Image Processing Toolbox.
% Скрипты определяют собственные пути; текущий каталог не меняется.
completedLabsRoot=fileparts(mfilename('fullpath'));
addpath(fullfile(completedLabsRoot,'Lab_02'));
addpath(fullfile(completedLabsRoot,'Lab_03'));
addpath(fullfile(completedLabsRoot,'Lab_04'));
run(fullfile(completedLabsRoot,'Lab_01','matrices.m'));
run(fullfile(completedLabsRoot,'Lab_01','autocontrast.m'));
run(fullfile(completedLabsRoot,'Lab_02','test_returnSubImage.m'));
run(fullfile(completedLabsRoot,'Lab_02','histograms.m'));
run(fullfile(completedLabsRoot,'Lab_03','test_intrans.m'));
run(fullfile(completedLabsRoot,'Lab_03','reproduce_transforms.m'));
run(fullfile(completedLabsRoot,'Lab_03','spatial_filtering.m'));
run(fullfile(completedLabsRoot,'Lab_04','edge_maps.m'));
run(fullfile(completedLabsRoot,'Lab_04','my_threshold.m'));
run(fullfile(completedLabsRoot,'Lab_04','my_hough.m'));
disp('Все четыре лабораторные выполнены. Результаты: Lab_XX/results_matlab.');
