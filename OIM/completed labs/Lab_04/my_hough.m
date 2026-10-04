%% Лабораторная работа 4. Часть 3. Хаф на карте Канни
labDir=fileparts(mfilename('fullpath'));
outDir=fullfile(labDir,'results_matlab');
if ~exist(outDir,'dir'), mkdir(outDir); end
% Пересчитываем карту, чтобы не зависеть от состояния Workspace.
building=imread(fullfile(labDir,'data','building.jpg'));
if size(building,3)==3, gray=rgb2gray(building); else, gray=building; end
f=edge(gray,'canny',[0.04 0.10],2);
% Пакет +labhough содержит функции из методички. Пространство имён
% исключает конфликт с современными одноимёнными функциями MATLAB.
addpath(labDir);
[H,theta,rho]=labhough.hough(f,0.5,1);
[r,c]=labhough.houghpeaks(H,30,0.25*max(H(:)),[25 15]);
lines=labhough.houghlines(f,theta,rho,r,c,15,40);
figure('Name','Lab 4: Hough accumulator');
imagesc(theta,rho,H); axis xy; colormap(gca,hot); colorbar;
xlabel('theta (degrees)'); ylabel('rho (pixels)'); hold on;
plot(theta(c),rho(r),'cs','MarkerSize',8); hold off;
figure('Name','Lab 4: detected segments');
for panel=1:2
    subplot(1,2,panel);
    if panel==1, imshow(f); title('Canny + segments');
    else, imshow(building); title('Original + segments'); end
    hold on;
    for idx=1:numel(lines)
        xy=[lines(idx).point1;lines(idx).point2];
        % Учебная функция возвращает (строка, столбец), не (x,y).
        plot(xy(:,2),xy(:,1),'g-','LineWidth',2);
    end
    hold off;
end
fprintf('Максимумов: %d; сегментов: %d\n',numel(r),numel(lines));
save(fullfile(outDir,'hough_results.mat'),'H','theta','rho','r','c','lines');
saveas(gcf,fullfile(outDir,'hough_lines.png'));
