function g = intrans(f, varargin)
%INTRANS Преобразования яркости, дополненные по заданию лабораторной 3.
% G=intrans(F,'neg'); G=intrans(F,'gamma',GAMMA);
% G=intrans(F,'log',C,CLASS); C=1, CLASS=class(F) по умолчанию.
% G=intrans(F,'stretch',M,E); M=mean(im2double(F)), E=4 по умолчанию.
% Сохраняет класс входа, кроме явного CLASS для логарифма.
narginchk(2,4);
validateattributes(f,{'uint8','uint16','double'},{'nonempty','real','finite'});
classin=class(f); method=validatestring(varargin{1},{'neg','log','gamma','stretch'});
% В исходнике пропущен логический оператор перед ~strcmp.
if isa(f,'double') && max(f(:))>1 && ~strcmp(method,'log')
    f=mat2gray(f);
else
    f=im2double(f);
end
switch method
    case 'neg'
        narginchk(2,2); g=imcomplement(f);
    case 'gamma'
        narginchk(3,3);
        gam=varargin{2};
        validateattributes(gam,{'numeric'},{'scalar','real','finite','positive'});
        g=imadjust(f,[],[],gam);
    case 'log'
        c=1;
        if numel(varargin)>=2, c=varargin{2}; end
        if numel(varargin)==3, classin=validatestring(varargin{3},{'uint8','uint16','double'}); end
        validateattributes(c,{'numeric'},{'scalar','real','finite','positive'});
        if any(f(:)<0), error('intrans:NegativeInput','Яркость не должна быть отрицательной.'); end
        g=c*log(1+f);
    case 'stretch'
        m=mean(f(:)); E=4;
        if numel(varargin)>=2, m=varargin{2}; end
        if numel(varargin)>=3, E=varargin{3}; end
        validateattributes(m,{'numeric'},{'scalar','real','finite','>=',0,'<=',1});
        validateattributes(E,{'numeric'},{'scalar','real','finite','positive'});
        g=1./(1+(m./(f+eps)).^E);
end
g=changeclass(classin,g);
end
