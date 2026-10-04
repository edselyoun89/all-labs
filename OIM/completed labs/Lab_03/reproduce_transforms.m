%% Лабораторная работа 3. Часть 2. Точное восстановление преобразований
labDir=fileparts(mfilename('fullpath')); addpath(labDir);
outDir=fullfile(labDir,'results_matlab');
if ~exist(outDir,'dir'), mkdir(outDir); end
f=imread(fullfile(labDir,'data','liftingbody_r0.png'));
d=im2double(f); m=mean(d(:));
results={intrans(f,'neg'),intrans(f,'stretch',m,10), ...
    intrans(f,'log',2),intrans(f,'gamma',3)};
labels={'Negative','Stretch: m=mean, E=10','Log: c=2','Gamma=3'};
figure('Name','Lab 3: reconstructed transformations');
subplot(2,3,1); imshow(f); title('Original');
for idx=1:4
    reference=imread(fullfile(labDir,'data',sprintf('liftingbody_r%d.png',idx)));
    delta=abs(double(results{idx})-double(reference));
    fprintf('r%d: different=%d; MAE=%.12g; max=%g\n',idx,nnz(delta),mean(delta(:)),max(delta(:)));
    assert(isequal(results{idx},reference),'Результат отличается от эталона.');
    subplot(2,3,idx+1); imshow(results{idx}); title(labels{idx});
    imwrite(results{idx},fullfile(outDir,sprintf('reproduced_r%d.png',idx)));
end
