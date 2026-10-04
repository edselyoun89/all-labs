%% Лабораторная работа 3. Часть 1. Шесть вариантов растяжения
labDir=fileparts(mfilename('fullpath')); addpath(labDir);
outDir=fullfile(labDir,'results_matlab');
if ~exist(outDir,'dir'), mkdir(outDir); end
if exist('tire.tif','file')
    tire=imread('tire.tif');
    fprintf('Использован стандартный tire.tif MATLAB.\n');
else
    tire=imread(fullfile(labDir,'data','tire_from_methodical.png'));
    fprintf('tire.tif отсутствует: используется изображение из PDF, см. REPORT.md.\n');
end
d=im2double(tire); m=mean(d(:));
params=[m 4;m 5;m 10;0.2 4;0.5 4;0.7 4];
figure('Name','Lab 3: six contrast transforms');
for idx=1:6
    result=intrans(tire,'stretch',params(idx,1),params(idx,2));
    subplot(2,3,idx); imshow(result);
    title(sprintf('m=%.4f, E=%g',params(idx,1),params(idx,2)));
    imwrite(result,fullfile(outDir,sprintf('stretch_%d.png',idx)));
end
assert(isequal(intrans(tire,'stretch'),intrans(tire,'stretch',m,4)));
assert(isequal(intrans(tire,'stretch',0.2),intrans(tire,'stretch',0.2,4)));
assert(isequal(intrans(uint8([0 255]),'neg'),uint8([255 0])));
assert(isequal(intrans(uint16([0 65535]),'gamma',1),uint16([0 65535])));
assert(isequal(intrans([0 10],'neg'),[1 0]));
assert(isa(intrans(tire,'log',2,'double'),'double'));
assert(all(isfinite(intrans(zeros(2),'stretch')),'all'));
