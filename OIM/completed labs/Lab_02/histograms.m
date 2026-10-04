%% Лабораторная работа 2. Часть 2. Эквализация и спецификация
labDir = fileparts(mfilename('fullpath')); addpath(labDir);
outDir = fullfile(labDir,'results_matlab');
if ~exist(outDir,'dir'), mkdir(outDir); end
flood = imread(fullfile(labDir,'data','flood.jpg'));
if size(flood,3)==3, flood=rgb2gray(flood); end
flood_eq = histeq(flood,256);
% Две моды: темная вода/окна и светлый фасад. Функция из комплекта.
p = twomodegauss(0.15,0.05,0.75,0.05,1,0.1,0.002);
flood_match = histeq(flood,p);
figure('Name','Lab 2: histograms');
subplot(3,2,1); imshow(flood); title('Original');
subplot(3,2,2); imhist(flood); title('Original histogram');
subplot(3,2,3); imshow(flood_eq); title('Equalization, 256 levels');
subplot(3,2,4); imhist(flood_eq); title('Equalized histogram');
subplot(3,2,5); imshow(flood_match); title('Bimodal specification');
subplot(3,2,6); imhist(flood_match); title('Specified histogram');
imwrite(flood_eq,fullfile(outDir,'flood_equalized.png'));
imwrite(flood_match,fullfile(outDir,'flood_matched.png'));
save(fullfile(outDir,'histograms.mat'),'p','flood','flood_eq','flood_match');
