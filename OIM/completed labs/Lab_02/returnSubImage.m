function subImage = returnSubImage(imageMatrix, startingRow, startingCol, squareSize)
%RETURNSUBIMAGE Квадрат N x N с сохранением всех цветовых каналов.
%   S = returnSubImage(I, ROW, COL) возвращает квадрат 100 x 100.
%   S = returnSubImage(I, ROW, COL, N) возвращает квадрат N x N.
%   Координаты начинаются с 1. Последняя строка равна ROW + N - 1.
narginchk(3,4);
if nargin < 4, squareSize = 100; end
validateattributes(imageMatrix,{'numeric','logical'},{'nonempty','real'},mfilename,'imageMatrix');
if ndims(imageMatrix)>3
    error('returnSubImage:Dimensions','Ожидается двумерное или RGB-изображение.');
end
validateattributes(startingRow,{'numeric'},{'scalar','real','finite','integer','positive'});
validateattributes(startingCol,{'numeric'},{'scalar','real','finite','integer','positive'});
validateattributes(squareSize,{'numeric'},{'scalar','real','finite','integer','positive'});
lastRow = double(startingRow) + double(squareSize) - 1;
lastCol = double(startingCol) + double(squareSize) - 1;
if lastRow > size(imageMatrix,1) || lastCol > size(imageMatrix,2)
    error('returnSubImage:OutOfBounds','Запрошенный квадрат выходит за границы изображения.');
end
subImage = imageMatrix(startingRow:lastRow,startingCol:lastCol,:);
end
