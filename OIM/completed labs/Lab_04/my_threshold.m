%% Лабораторная работа 4. Часть 2. Автоматический глобальный порог
labDir=fileparts(mfilename('fullpath'));
outDir=fullfile(labDir,'results_matlab');
if ~exist(outDir,'dir'), mkdir(outDir); end
f=imread(fullfile(labDir,'data','text.jpg'));
if size(f,3)==3, f=rgb2gray(f); end
d=double(f); T=0.5*(min(d(:))+max(d(:))); history=T;
for iteration=1:1000
    g=d>=T;
    if all(g(:)) || ~any(g(:)), break; end
    Tnext=0.5*(mean(d(g))+mean(d(~g)));
    history(end+1)=Tnext;
    done=abs(Tnext-T)<0.5;
    T=Tnext;
    if done, break; end
end
binaryIterative=d>=T;
T_otsu=graythresh(f); T_otsu_255=255*T_otsu;
binaryOtsu=im2double(f)>T_otsu;
fprintf('Итеративный T=%.10f, итераций=%d\n',T,numel(history)-1);
fprintf('Отсу: T=%.10f, 255*T=%.10f\n',T_otsu,T_otsu_255);
figure('Name','Lab 4: automatic threshold');
subplot(3,1,1); imshow(f); title('Original');
subplot(3,1,2); imshow(binaryIterative); title(sprintf('Iterative: T=%.4f',T));
subplot(3,1,3); imshow(binaryOtsu); title(sprintf('Otsu: T=%.4f',T_otsu_255));
imwrite(binaryIterative,fullfile(outDir,'text_iterative.png'));
imwrite(binaryOtsu,fullfile(outDir,'text_otsu.png'));
save(fullfile(outDir,'thresholds.mat'),'T','T_otsu','history');
