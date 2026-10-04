%% Лабораторная работа 1. Часть 2. Автоматическая настройка контраста
labDir = fileparts(mfilename('fullpath'));
outDir = fullfile(labDir,'results_matlab');
if ~exist(outDir,'dir'), mkdir(outDir); end
image = double(load(fullfile(labDir,'data','image.dat')));
i_low = min(image(:));
i_high = max(image(:));
i_mean = mean(image(:));
image2 = image - i_low;
if i_high > i_low
    k = 255 / (i_high-i_low);
else
    k = 0; % У постоянного изображения нет диапазона для растяжения.
end
image3 = image2 * k;
fprintf('i_low = %.10g; i_high = %.10g; i_mean = %.10g; k = %.10g\n', ...
    i_low,i_high,i_mean,k);
% Double с диапазоном 0..255 надо преобразовать в uint8 для imshow.
figure('Name','Lab 1: autocontrast');
subplot(1,3,1); imshow(uint8(image)); title('Original');
subplot(1,3,2); imshow(uint8(image2)); title('Subtract minimum');
subplot(1,3,3); imshow(uint8(image3)); title('Stretch to 0..255');
imwrite(uint8(image),fullfile(outDir,'original.png'));
imwrite(uint8(image2),fullfile(outDir,'shifted.png'));
imwrite(uint8(image3),fullfile(outDir,'autocontrast.png'));
save(fullfile(outDir,'measurements.mat'),'i_low','i_high','i_mean','k','image3');
