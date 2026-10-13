// Um só lugar para os ícones do app: traço de 1.5, como o editor de referência. Troca de biblioteca
// ou de espessura acontece aqui e vale para a tela inteira.
import {
  AlignCenter,
  AlignJustify,
  AlignLeft,
  AlignRight,
  ArrowLeft,
  ArrowRight,
  Bold,
  BookOpen,
  Bookmark,
  Check,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  CloudDownload,
  Copy,
  Download,
  FileText,
  Globe,
  Heart,
  History,
  Italic,
  Layers,
  List,
  ListOrdered,
  Mail,
  MessageCircle,
  Newspaper,
  Pencil,
  Plus,
  Presentation,
  Save,
  Send,
  Settings,
  SignalHigh,
  SignalLow,
  SignalMedium,
  Trash2,
  Type,
  Underline,
  Upload,
  User,
  X,
  ChevronDown,
  ChartNoAxesColumn,
  Ellipsis,
  FileUp,
  Highlighter,
  Images,
  Landmark,
  LoaderCircle,
  Palette,
  Play,
  Quote,
  RefreshCw,
  Redo2,
  Scale,
  Smartphone,
  Sparkles,
  Strikethrough,
  TriangleAlert,
  Undo2,
  WandSparkles,
  type LucideProps,
} from "lucide-react";

const TRACO = 1.5;

export function com(Icone: React.ComponentType<LucideProps>) {
  return function IconeDoApp({ size = 22, ...resto }: LucideProps) {
    return <Icone size={size} strokeWidth={TRACO} aria-hidden="true" {...resto} />;
  };
}

export const IconeIngestao = com(Layers);
export const IconeTexto = com(FileText);
export const IconeCarrossel = com(Presentation);
export const IconeVideo = com(Clapperboard);
export const IconeHistorico = com(History);
export const IconeConfiguracoes = com(Settings);
export const IconePessoa = com(User);
export const IconeSeta = com(ChevronRight);
export const IconeVoltarSeta = com(ChevronLeft);
export const IconeParaDireita = com(ArrowRight);
export const IconeParaEsquerda = com(ArrowLeft);
export const IconeMais = com(Plus);
export const IconeMarca = com(Check);
export const IconeFechar = com(X);
export const IconeEnviar = com(Upload);
export const IconeBaixar = com(Download);
export const IconeBuscar = com(CloudDownload);
export const IconeLixo = com(Trash2);
export const IconeCopiar = com(Copy);
export const IconeLapis = com(Pencil);
export const IconeSalvar = com(Save);
export const IconeNegrito = com(Bold);
export const IconeItalico = com(Italic);
export const IconeSublinhado = com(Underline);
export const IconeEsquerda = com(AlignLeft);
export const IconeCentro = com(AlignCenter);
export const IconeDireita = com(AlignRight);
export const IconeJustificado = com(AlignJustify);
export const IconeLista = com(List);
export const IconeListaNumerada = com(ListOrdered);
export const IconeLetra = com(Type);
export const IconeEmail = com(Mail);
export const IconeJornal = com(Newspaper);
export const IconeSite = com(Globe);
export const IconeLivro = com(BookOpen);
export const IconeCurtir = com(Heart);
export const IconeComentar = com(MessageCircle);
export const IconeCompartilhar = com(Send);
export const IconeGuardar = com(Bookmark);
export const IconeNivel1 = com(SignalLow);
export const IconeNivel2 = com(SignalMedium);
export const IconeNivel3 = com(SignalHigh);
export const IconeBanco = com(Landmark);
export const IconeBalanca = com(Scale);
export const IconeGrafico = com(ChartNoAxesColumn);
export const IconeArquivoMais = com(FileUp);
export const IconeAtualizar = com(RefreshCw);
export const IconeGirando = com(LoaderCircle);
export const IconePaleta = com(Palette);
export const IconeBrilho = com(Sparkles);
export const IconeVarinha = com(WandSparkles);
export const IconeTocar = com(Play);
export const IconeCelular = com(Smartphone);
export const IconeImagens = com(Images);
export const IconeAspas = com(Quote);
export const IconeReticencias = com(Ellipsis);
export const IconeAlerta = com(TriangleAlert);
export const IconeDesfazer = com(Undo2);
export const IconeRefazer = com(Redo2);
export const IconeTachado = com(Strikethrough);
export const IconeMarcaTexto = com(Highlighter);
export const IconeBaixo = com(ChevronDown);
