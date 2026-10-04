%% Лабораторная работа 2. Часть 1. Фрагменты и проверка границ
labDir = fileparts(mfilename('fullpath')); addpath(labDir);
outDir = fullfile(labDir,'results_matlab');
if ~exist(outDir,'dir'), mkdir(outDir); end
lifting = imread(fullfile(labDir,'data','liftingbody.jpg'));
lifting_sub1 = returnSubImage(lifting,159,33,330);
lifting_sub2 = returnSubImage(lifting,110,360);
assert(isequal(size(lifting_sub1),[330 330 3]));
assert(isequal(size(lifting_sub2),[100 100 3]));
assert(isequal(returnSubImage(lifting,511,511,1),lifting(511,511,:)));
didThrow = false;
try
    returnSubImage(lifting,159,33,500);
catch exception
    didThrow = strcmp(exception.identifier,'returnSubImage:OutOfBounds');
    if ~didThrow, rethrow(exception); end
    fprintf('Ожидаемая ошибка: %s\n',exception.message);
end
assert(didThrow,'Не обнаружен выход за границы.');
figure('Name','Lab 2: subimages');
subplot(1,3,1); imshow(lifting); title('Original');
subplot(1,3,2); imshow(lifting_sub1); title('330 x 330');
subplot(1,3,3); imshow(lifting_sub2); title('100 x 100');
imwrite(lifting_sub1,fullfile(outDir,'lifting_sub1.png'));
imwrite(lifting_sub2,fullfile(outDir,'lifting_sub2.png'));
