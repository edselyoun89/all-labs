%% Лабораторная работа 4. Часть 1. Контурные карты
% На стр. 12: изображение 1 - Canny, изображение 2 - zerocross.
% Canny даёт связные тонкие границы с меньшим количеством текстуры.
% Приложенный building.jpg имеет другое кадрирование, чем образец PDF.
labDir=fileparts(mfilename('fullpath'));
outDir=fullfile(labDir,'results_matlab');
if ~exist(outDir,'dir'), mkdir(outDir); end
building=imread(fullfile(labDir,'data','building.jpg'));
if size(building,3)==3, gray=rgb2gray(building); else, gray=building; end
cannyThreshold=[0.04 0.10]; cannySigma=2;
cannyMap=edge(gray,'canny',cannyThreshold,cannySigma);
zeroSigma=2; zeroThreshold=0.002;
logFilter=fspecial('log',13,zeroSigma);
zeroMap=edge(gray,'zerocross',zeroThreshold,logFilter);
figure('Name','Lab 4: edge maps');
subplot(1,3,1); imshow(building); title('Supplied building.jpg');
subplot(1,3,2); imshow(cannyMap); title('Canny');
subplot(1,3,3); imshow(zeroMap); title('Zero crossings');
imwrite(cannyMap,fullfile(outDir,'canny.png'));
imwrite(zeroMap,fullfile(outDir,'zerocross.png'));
save(fullfile(outDir,'edge_maps.mat'),'cannyMap','zeroMap','cannyThreshold','cannySigma','zeroThreshold','zeroSigma');
