%% Лабораторная работа 3. Часть 3. Горизонтальные и вертикальные края
labDir=fileparts(mfilename('fullpath'));
outDir=fullfile(labDir,'results_matlab');
if ~exist(outDir,'dir'), mkdir(outDir); end
cats=imread(fullfile(labDir,'data','two_cats.jpg'));
% Сохраняем RGB и uint8, как в примере методички: отрицательные
% отклики обрезаются, а сумма насыщается на 255.
h=fspecial('sobel');
horizontal=imfilter(cats,h,0,'corr','same');
vertical=imfilter(cats,h.',0,'corr','same');
combined=imadd(horizontal,vertical);
figure('Name','Lab 3: spatial filtering');
subplot(2,2,1); imshow(cats); title('Original');
subplot(2,2,2); imshow(horizontal); title('Horizontal edges');
subplot(2,2,3); imshow(vertical); title('Vertical edges');
subplot(2,2,4); imshow(combined); title('Saturated sum');
imwrite(horizontal,fullfile(outDir,'horizontal.png'));
imwrite(vertical,fullfile(outDir,'vertical.png'));
imwrite(combined,fullfile(outDir,'combined.png'));
