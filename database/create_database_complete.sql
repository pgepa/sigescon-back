--
-- PostgreSQL database dump
--

\restrict UPNCYsPfe49y4gufX2paYRv6Hzdx14efTlAv4s3EEoJLMGWs5UVdSvoLvISRP7G

-- Dumped from database version 17.9 (Ubuntu 17.9-1.pgdg24.04+1)
-- Dumped by pg_dump version 17.9 (Ubuntu 17.9-1.pgdg24.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: limpar_audit_logs_antigos(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.limpar_audit_logs_antigos(dias_retencao integer DEFAULT 365) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    registros_deletados INTEGER;
BEGIN
    DELETE FROM audit_log
    WHERE data_hora < CURRENT_TIMESTAMP - (dias_retencao || ' days')::INTERVAL;

    GET DIAGNOSTICS registros_deletados = ROW_COUNT;
    RETURN registros_deletados;
END;
$$;


--
-- Name: update_termo_contratual_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_termo_contratual_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW."updatedAt" = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: arquivo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.arquivo (
    id integer NOT NULL,
    nome_arquivo character varying(255) NOT NULL,
    caminho_arquivo text NOT NULL,
    tamanho_bytes bigint,
    tipo_mime character varying(100),
    contrato_id integer,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    tipo_vinculo character varying(20) DEFAULT 'contrato'::character varying,
    CONSTRAINT arquivo_tipo_vinculo_check CHECK (((tipo_vinculo)::text = ANY ((ARRAY['contrato'::character varying, 'termo_aditivo'::character varying, 'relatorio'::character varying])::text[])))
);


--
-- Name: arquivo_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.arquivo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: arquivo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.arquivo_id_seq OWNED BY public.arquivo.id;


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    usuario_nome character varying(255) NOT NULL,
    perfil_usado character varying(50),
    acao character varying(100) NOT NULL,
    entidade character varying(100) NOT NULL,
    entidade_id integer,
    descricao text NOT NULL,
    dados_anteriores jsonb,
    dados_novos jsonb,
    ip_address character varying(45),
    user_agent text,
    data_hora timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT audit_log_acao_check CHECK (((acao)::text = ANY (ARRAY[('CRIAR'::character varying)::text, ('ATUALIZAR'::character varying)::text, ('DELETAR'::character varying)::text, ('ATIVAR'::character varying)::text, ('DESATIVAR'::character varying)::text, ('APROVAR'::character varying)::text, ('REJEITAR'::character varying)::text, ('ENVIAR'::character varying)::text, ('CONCLUIR'::character varying)::text, ('CANCELAR'::character varying)::text, ('LOGIN'::character varying)::text, ('LOGOUT'::character varying)::text, ('ALTERNAR_PERFIL'::character varying)::text, ('UPLOAD'::character varying)::text, ('DOWNLOAD'::character varying)::text, ('REMOVER_ARQUIVO'::character varying)::text, ('CRIAR_PENDENCIAS_AUTOMATICAS'::character varying)::text, ('ATUALIZAR_CONFIG'::character varying)::text])))
);


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: clientes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clientes (
    id_cliente integer NOT NULL,
    nome character varying(100) NOT NULL,
    cidade character varying(100) NOT NULL
);


--
-- Name: configuracao_sistema; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configuracao_sistema (
    id integer NOT NULL,
    chave character varying(100) NOT NULL,
    valor text,
    descricao text,
    tipo character varying(50) DEFAULT 'string'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: configuracao_sistema_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.configuracao_sistema_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: configuracao_sistema_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.configuracao_sistema_id_seq OWNED BY public.configuracao_sistema.id;


--
-- Name: contratado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contratado (
    id integer NOT NULL,
    nome character varying(255) NOT NULL,
    cnpj character varying(18),
    cpf character varying(14),
    email character varying(255),
    telefone character varying(20),
    endereco text,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: contratado_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contratado_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contratado_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contratado_id_seq OWNED BY public.contratado.id;


--
-- Name: contrato; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contrato (
    id integer NOT NULL,
    nr_contrato character varying(50) NOT NULL,
    objeto text NOT NULL,
    valor_anual numeric(15,2),
    valor_global numeric(15,2),
    base_legal text,
    data_inicio date,
    data_fim date,
    termos_contratuais text,
    contratado_id integer NOT NULL,
    modalidade_id integer NOT NULL,
    status_id integer NOT NULL,
    gestor_id integer NOT NULL,
    fiscal_id integer NOT NULL,
    fiscal_substituto_id integer,
    pae text,
    doe text,
    data_doe date,
    documento text,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    garantia date
);


--
-- Name: contrato_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contrato_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contrato_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contrato_id_seq OWNED BY public.contrato.id;


--
-- Name: modalidade; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.modalidade (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: modalidade_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.modalidade_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: modalidade_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.modalidade_id_seq OWNED BY public.modalidade.id;


--
-- Name: notification_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_log (
    id integer NOT NULL,
    notification_type character varying(50) NOT NULL,
    contrato_id integer NOT NULL,
    alert_milestone integer NOT NULL,
    sent_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: notification_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notification_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notification_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notification_log_id_seq OWNED BY public.notification_log.id;


--
-- Name: ocorrencia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ocorrencia (
    id integer NOT NULL,
    contrato_id integer NOT NULL,
    fiscal_usuario_id integer NOT NULL,
    tipo_ocorrencia_id integer NOT NULL,
    descricao text NOT NULL,
    data_ocorrencia timestamp without time zone NOT NULL,
    data_ciencia_contratado timestamp without time zone,
    resposta_contratado text,
    prazo_resolucao timestamp without time zone,
    arquivo_id integer,
    relatorio_id integer,
    status_id integer,
    ativo boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: ocorrencia_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ocorrencia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ocorrencia_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ocorrencia_id_seq OWNED BY public.ocorrencia.id;


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset_tokens (
    id integer NOT NULL,
    token character varying(255) NOT NULL,
    usuario_id integer NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    used_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.password_reset_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.password_reset_tokens_id_seq OWNED BY public.password_reset_tokens.id;


--
-- Name: pedidos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pedidos (
    id_pedido integer NOT NULL,
    data_pedido date NOT NULL,
    valor numeric(10,2) NOT NULL,
    id_cliente integer NOT NULL
);


--
-- Name: pendenciarelatorio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pendenciarelatorio (
    id integer NOT NULL,
    contrato_id integer NOT NULL,
    titulo character varying(255) NOT NULL,
    descricao text,
    data_prazo date NOT NULL,
    status_pendencia_id integer NOT NULL,
    criado_por_usuario_id integer NOT NULL,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: pendenciarelatorio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pendenciarelatorio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pendenciarelatorio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pendenciarelatorio_id_seq OWNED BY public.pendenciarelatorio.id;


--
-- Name: perfil; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.perfil (
    id integer NOT NULL,
    nome character varying(50) NOT NULL,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: perfil_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.perfil_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: perfil_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.perfil_id_seq OWNED BY public.perfil.id;


--
-- Name: relatorio_fiscalizacao_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.relatorio_fiscalizacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: relatorio_fiscalizacao; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.relatorio_fiscalizacao (
    id integer DEFAULT nextval('public.relatorio_fiscalizacao_id_seq'::regclass) NOT NULL,
    contrato_id integer,
    periodo_inicio date,
    periodo_fim date,
    data_relatorio date,
    execucao_objeto_sim boolean NOT NULL,
    execucao_objeto_detalhes text,
    prazo_execucao_sim boolean NOT NULL,
    prazo_execucao_detalhes text,
    nivel_qualidade_sim boolean NOT NULL,
    nivel_qualidade_detalhes text,
    medicoes_servicos_sim boolean NOT NULL,
    medicoes_servicos_detalhes text,
    ocorrencias_sim boolean NOT NULL,
    ocorrencias_detalhes text,
    documentos_habilitacao_sim boolean NOT NULL,
    documentos_habilitacao_detalhes text,
    subcontratacao_sim boolean NOT NULL,
    subcontratacao_detalhes text,
    obrigacoes_empregados_resposta text NOT NULL,
    obrigacoes_empregados_detalhes text,
    garantias_contratuais_resposta text NOT NULL,
    garantias_contratuais_detalhes text,
    execucao_satisfatoria_sim boolean NOT NULL,
    execucao_satisfatoria_detalhes text,
    created_at date,
    updated_at date,
    status character varying(50) DEFAULT 'finalizado'::character varying NOT NULL
);


--
-- Name: relatoriofiscal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.relatoriofiscal (
    id integer NOT NULL,
    contrato_id integer NOT NULL,
    pendencia_id integer,
    titulo character varying(255),
    descricao text,
    observacoes text,
    fiscal_usuario_id integer NOT NULL,
    aprovador_usuario_id integer,
    arquivo_id integer,
    status_id integer NOT NULL,
    data_envio timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_analise timestamp without time zone,
    observacoes_analise text,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: relatoriofiscal_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.relatoriofiscal_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: relatoriofiscal_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.relatoriofiscal_id_seq OWNED BY public.relatoriofiscal.id;


--
-- Name: session_context; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_context (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    perfil_ativo_id integer NOT NULL,
    sessao_id character varying(255) NOT NULL,
    data_criacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_expiracao timestamp without time zone,
    ativo boolean DEFAULT true
);


--
-- Name: session_context_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.session_context_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: session_context_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.session_context_id_seq OWNED BY public.session_context.id;


--
-- Name: status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.status (
    id integer NOT NULL,
    nome character varying(50) NOT NULL,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: status_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.status_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.status_id_seq OWNED BY public.status.id;


--
-- Name: statuspendencia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.statuspendencia (
    id integer NOT NULL,
    nome character varying(50) NOT NULL,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: statuspendencia_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.statuspendencia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: statuspendencia_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.statuspendencia_id_seq OWNED BY public.statuspendencia.id;


--
-- Name: statusrelatorio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.statusrelatorio (
    id integer NOT NULL,
    nome character varying(50) NOT NULL,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: statusrelatorio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.statusrelatorio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: statusrelatorio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.statusrelatorio_id_seq OWNED BY public.statusrelatorio.id;


--
-- Name: termo_aditivo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.termo_aditivo (
    id integer NOT NULL,
    contrato_id integer NOT NULL,
    numero_aditivo integer NOT NULL,
    tipo character varying(50) NOT NULL,
    objeto text NOT NULL,
    data_assinatura date NOT NULL,
    data_publicacao date,
    nova_data_fim date,
    valor_acrescimo numeric(15,2),
    valor_supressao numeric(15,2),
    arquivo_id integer,
    observacoes text,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    pae text
);


--
-- Name: termo_aditivo_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.termo_aditivo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: termo_aditivo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.termo_aditivo_id_seq OWNED BY public.termo_aditivo.id;


--
-- Name: termo_contratual_old; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.termo_contratual_old (
    id integer NOT NULL,
    nome character varying(50) NOT NULL,
    "createdAt" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updatedAt" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: termo_contratual_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.termo_contratual_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: termo_contratual_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.termo_contratual_id_seq OWNED BY public.termo_contratual_old.id;


--
-- Name: tipo_ocorrencia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_ocorrencia (
    id integer NOT NULL,
    nome character varying(150) NOT NULL,
    gera_penalidade boolean DEFAULT false NOT NULL,
    gera_prazo boolean DEFAULT false NOT NULL,
    prazo_padrao_dias integer,
    ativo boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: tipo_ocorrencia_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_ocorrencia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_ocorrencia_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_ocorrencia_id_seq OWNED BY public.tipo_ocorrencia.id;


--
-- Name: usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario (
    id integer NOT NULL,
    nome character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    matricula character varying(50),
    cpf character varying(14),
    senha_hash character varying(255) NOT NULL,
    perfil_id integer,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: usuario_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_id_seq OWNED BY public.usuario.id;


--
-- Name: usuario_perfil; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_perfil (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    perfil_id integer NOT NULL,
    concedido_por_usuario_id integer,
    data_concessao timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: usuario_perfil_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_perfil_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_perfil_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_perfil_id_seq OWNED BY public.usuario_perfil.id;


--
-- Name: v_usuario_perfis; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_usuario_perfis AS
 SELECT u.id AS usuario_id,
    u.nome AS usuario_nome,
    u.email AS usuario_email,
    u.matricula AS usuario_matricula,
    p.id AS perfil_id,
    p.nome AS perfil_nome,
    up.data_concessao,
    up.ativo AS perfil_ativo
   FROM ((public.usuario u
     JOIN public.usuario_perfil up ON ((u.id = up.usuario_id)))
     JOIN public.perfil p ON ((up.perfil_id = p.id)))
  WHERE ((u.ativo = true) AND (up.ativo = true) AND (p.ativo = true));


--
-- Name: arquivo id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.arquivo ALTER COLUMN id SET DEFAULT nextval('public.arquivo_id_seq'::regclass);


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: configuracao_sistema id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracao_sistema ALTER COLUMN id SET DEFAULT nextval('public.configuracao_sistema_id_seq'::regclass);


--
-- Name: contratado id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contratado ALTER COLUMN id SET DEFAULT nextval('public.contratado_id_seq'::regclass);


--
-- Name: contrato id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato ALTER COLUMN id SET DEFAULT nextval('public.contrato_id_seq'::regclass);


--
-- Name: modalidade id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modalidade ALTER COLUMN id SET DEFAULT nextval('public.modalidade_id_seq'::regclass);


--
-- Name: notification_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_log ALTER COLUMN id SET DEFAULT nextval('public.notification_log_id_seq'::regclass);


--
-- Name: ocorrencia id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencia ALTER COLUMN id SET DEFAULT nextval('public.ocorrencia_id_seq'::regclass);


--
-- Name: password_reset_tokens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens ALTER COLUMN id SET DEFAULT nextval('public.password_reset_tokens_id_seq'::regclass);


--
-- Name: pendenciarelatorio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pendenciarelatorio ALTER COLUMN id SET DEFAULT nextval('public.pendenciarelatorio_id_seq'::regclass);


--
-- Name: perfil id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil ALTER COLUMN id SET DEFAULT nextval('public.perfil_id_seq'::regclass);


--
-- Name: relatoriofiscal id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatoriofiscal ALTER COLUMN id SET DEFAULT nextval('public.relatoriofiscal_id_seq'::regclass);


--
-- Name: session_context id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_context ALTER COLUMN id SET DEFAULT nextval('public.session_context_id_seq'::regclass);


--
-- Name: status id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status ALTER COLUMN id SET DEFAULT nextval('public.status_id_seq'::regclass);


--
-- Name: statuspendencia id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statuspendencia ALTER COLUMN id SET DEFAULT nextval('public.statuspendencia_id_seq'::regclass);


--
-- Name: statusrelatorio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statusrelatorio ALTER COLUMN id SET DEFAULT nextval('public.statusrelatorio_id_seq'::regclass);


--
-- Name: termo_aditivo id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.termo_aditivo ALTER COLUMN id SET DEFAULT nextval('public.termo_aditivo_id_seq'::regclass);


--
-- Name: termo_contratual_old id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.termo_contratual_old ALTER COLUMN id SET DEFAULT nextval('public.termo_contratual_id_seq'::regclass);


--
-- Name: tipo_ocorrencia id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_ocorrencia ALTER COLUMN id SET DEFAULT nextval('public.tipo_ocorrencia_id_seq'::regclass);


--
-- Name: usuario id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id SET DEFAULT nextval('public.usuario_id_seq'::regclass);


--
-- Name: usuario_perfil id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_perfil ALTER COLUMN id SET DEFAULT nextval('public.usuario_perfil_id_seq'::regclass);


--
-- Name: arquivo arquivo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.arquivo
    ADD CONSTRAINT arquivo_pkey PRIMARY KEY (id);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: clientes clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_pkey PRIMARY KEY (id_cliente);


--
-- Name: configuracao_sistema configuracao_sistema_chave_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracao_sistema
    ADD CONSTRAINT configuracao_sistema_chave_key UNIQUE (chave);


--
-- Name: configuracao_sistema configuracao_sistema_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracao_sistema
    ADD CONSTRAINT configuracao_sistema_pkey PRIMARY KEY (id);


--
-- Name: contratado contratado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contratado
    ADD CONSTRAINT contratado_pkey PRIMARY KEY (id);


--
-- Name: contrato contrato_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato
    ADD CONSTRAINT contrato_pkey PRIMARY KEY (id);


--
-- Name: modalidade modalidade_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modalidade
    ADD CONSTRAINT modalidade_pkey PRIMARY KEY (id);


--
-- Name: notification_log notification_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_log
    ADD CONSTRAINT notification_log_pkey PRIMARY KEY (id);


--
-- Name: ocorrencia ocorrencia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencia
    ADD CONSTRAINT ocorrencia_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: pedidos pedidos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_pkey PRIMARY KEY (id_pedido);


--
-- Name: pendenciarelatorio pendenciarelatorio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pendenciarelatorio
    ADD CONSTRAINT pendenciarelatorio_pkey PRIMARY KEY (id);


--
-- Name: perfil perfil_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.perfil
    ADD CONSTRAINT perfil_pkey PRIMARY KEY (id);


--
-- Name: relatorio_fiscalizacao relatorio_fiscalizacao_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatorio_fiscalizacao
    ADD CONSTRAINT relatorio_fiscalizacao_pkey PRIMARY KEY (id);


--
-- Name: relatoriofiscal relatoriofiscal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatoriofiscal
    ADD CONSTRAINT relatoriofiscal_pkey PRIMARY KEY (id);


--
-- Name: session_context session_context_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_context
    ADD CONSTRAINT session_context_pkey PRIMARY KEY (id);


--
-- Name: status status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status
    ADD CONSTRAINT status_pkey PRIMARY KEY (id);


--
-- Name: statuspendencia statuspendencia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statuspendencia
    ADD CONSTRAINT statuspendencia_pkey PRIMARY KEY (id);


--
-- Name: statusrelatorio statusrelatorio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statusrelatorio
    ADD CONSTRAINT statusrelatorio_pkey PRIMARY KEY (id);


--
-- Name: termo_aditivo termo_aditivo_contrato_id_numero_aditivo_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.termo_aditivo
    ADD CONSTRAINT termo_aditivo_contrato_id_numero_aditivo_key UNIQUE (contrato_id, numero_aditivo);


--
-- Name: termo_aditivo termo_aditivo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.termo_aditivo
    ADD CONSTRAINT termo_aditivo_pkey PRIMARY KEY (id);


--
-- Name: termo_contratual_old termo_contratual_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.termo_contratual_old
    ADD CONSTRAINT termo_contratual_pkey PRIMARY KEY (id);


--
-- Name: tipo_ocorrencia tipo_ocorrencia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_ocorrencia
    ADD CONSTRAINT tipo_ocorrencia_pkey PRIMARY KEY (id);


--
-- Name: notification_log unique_notification; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_log
    ADD CONSTRAINT unique_notification UNIQUE (notification_type, contrato_id, alert_milestone);


--
-- Name: termo_contratual_old uq_termo_contratual_nome; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.termo_contratual_old
    ADD CONSTRAINT uq_termo_contratual_nome UNIQUE (nome);


--
-- Name: usuario_perfil usuario_perfil_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_perfil
    ADD CONSTRAINT usuario_perfil_pkey PRIMARY KEY (id);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id);


--
-- Name: idx_audit_log_acao; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_acao ON public.audit_log USING btree (acao);


--
-- Name: idx_audit_log_data_hora; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_data_hora ON public.audit_log USING btree (data_hora DESC);


--
-- Name: idx_audit_log_entidade; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_entidade ON public.audit_log USING btree (entidade, entidade_id);


--
-- Name: idx_audit_log_perfil; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_perfil ON public.audit_log USING btree (perfil_usado);


--
-- Name: idx_audit_log_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_usuario_id ON public.audit_log USING btree (usuario_id);


--
-- Name: idx_contrato_contratado_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contrato_contratado_id ON public.contrato USING btree (contratado_id);


--
-- Name: idx_contrato_data_fim; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contrato_data_fim ON public.contrato USING btree (data_fim);


--
-- Name: idx_contrato_fiscal_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contrato_fiscal_id ON public.contrato USING btree (fiscal_id);


--
-- Name: idx_contrato_gestor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contrato_gestor_id ON public.contrato USING btree (gestor_id);


--
-- Name: idx_contrato_modalidade_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contrato_modalidade_id ON public.contrato USING btree (modalidade_id);


--
-- Name: idx_contrato_status_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contrato_status_id ON public.contrato USING btree (status_id);


--
-- Name: idx_notification_log_contrato_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notification_log_contrato_id ON public.notification_log USING btree (contrato_id);


--
-- Name: idx_notification_log_sent_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notification_log_sent_at ON public.notification_log USING btree (sent_at);


--
-- Name: idx_notification_log_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notification_log_type ON public.notification_log USING btree (notification_type);


--
-- Name: idx_ocorrencia_contrato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencia_contrato ON public.ocorrencia USING btree (contrato_id);


--
-- Name: idx_ocorrencia_data; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencia_data ON public.ocorrencia USING btree (data_ocorrencia);


--
-- Name: idx_ocorrencia_fiscal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencia_fiscal ON public.ocorrencia USING btree (fiscal_usuario_id);


--
-- Name: idx_ocorrencia_relatorio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencia_relatorio ON public.ocorrencia USING btree (relatorio_id);


--
-- Name: idx_ocorrencia_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencia_status ON public.ocorrencia USING btree (status_id);


--
-- Name: idx_password_reset_tokens_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_password_reset_tokens_expires_at ON public.password_reset_tokens USING btree (expires_at);


--
-- Name: idx_password_reset_tokens_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_password_reset_tokens_usuario_id ON public.password_reset_tokens USING btree (usuario_id);


--
-- Name: idx_pendenciarelatorio_contrato_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pendenciarelatorio_contrato_id ON public.pendenciarelatorio USING btree (contrato_id);


--
-- Name: idx_pendenciarelatorio_data_prazo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pendenciarelatorio_data_prazo ON public.pendenciarelatorio USING btree (data_prazo);


--
-- Name: idx_relatoriofiscal_contrato_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_relatoriofiscal_contrato_id ON public.relatoriofiscal USING btree (contrato_id);


--
-- Name: idx_session_context_sessao_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_context_sessao_id ON public.session_context USING btree (sessao_id) WHERE (ativo IS TRUE);


--
-- Name: idx_session_context_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_session_context_usuario_id ON public.session_context USING btree (usuario_id) WHERE (ativo IS TRUE);


--
-- Name: idx_termo_aditivo_contrato_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_termo_aditivo_contrato_id ON public.termo_aditivo USING btree (contrato_id) WHERE (ativo IS TRUE);


--
-- Name: idx_termo_contratual_nome; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_termo_contratual_nome ON public.termo_contratual_old USING btree (nome);


--
-- Name: idx_unique_contratado_cnpj_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_contratado_cnpj_ativo ON public.contratado USING btree (cnpj) WHERE ((ativo IS TRUE) AND (cnpj IS NOT NULL));


--
-- Name: idx_unique_contratado_cpf_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_contratado_cpf_ativo ON public.contratado USING btree (cpf) WHERE ((ativo IS TRUE) AND (cpf IS NOT NULL));


--
-- Name: idx_unique_contratado_email_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_contratado_email_ativo ON public.contratado USING btree (email) WHERE ((ativo IS TRUE) AND (email IS NOT NULL));


--
-- Name: idx_unique_contrato_nr_contrato_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_contrato_nr_contrato_ativo ON public.contrato USING btree (nr_contrato) WHERE (ativo IS TRUE);


--
-- Name: idx_unique_modalidade_nome_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_modalidade_nome_ativo ON public.modalidade USING btree (nome) WHERE (ativo IS TRUE);


--
-- Name: idx_unique_password_reset_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_password_reset_token ON public.password_reset_tokens USING btree (token);


--
-- Name: idx_unique_perfil_nome_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_perfil_nome_ativo ON public.perfil USING btree (nome) WHERE (ativo IS TRUE);


--
-- Name: idx_unique_status_nome_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_status_nome_ativo ON public.status USING btree (nome) WHERE (ativo IS TRUE);


--
-- Name: idx_unique_statuspendencia_nome_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_statuspendencia_nome_ativo ON public.statuspendencia USING btree (nome) WHERE (ativo IS TRUE);


--
-- Name: idx_unique_statusrelatorio_nome_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_statusrelatorio_nome_ativo ON public.statusrelatorio USING btree (nome) WHERE (ativo IS TRUE);


--
-- Name: idx_unique_usuario_cpf_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_usuario_cpf_ativo ON public.usuario USING btree (cpf) WHERE (ativo IS TRUE);


--
-- Name: idx_unique_usuario_email_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_usuario_email_ativo ON public.usuario USING btree (email) WHERE (ativo IS TRUE);


--
-- Name: idx_unique_usuario_matricula_ativo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_unique_usuario_matricula_ativo ON public.usuario USING btree (matricula) WHERE (ativo IS TRUE);


--
-- Name: idx_usuario_perfil_perfil_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_perfil_perfil_id ON public.usuario_perfil USING btree (perfil_id) WHERE (ativo IS TRUE);


--
-- Name: idx_usuario_perfil_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usuario_perfil_usuario_id ON public.usuario_perfil USING btree (usuario_id) WHERE (ativo IS TRUE);


--
-- Name: relatoriofiscal_arquivo_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX relatoriofiscal_arquivo_id_key ON public.relatoriofiscal USING btree (arquivo_id) WHERE (arquivo_id IS NOT NULL);


--
-- Name: session_context_sessao_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX session_context_sessao_id_key ON public.session_context USING btree (sessao_id);


--
-- Name: usuario_perfil_usuario_id_perfil_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX usuario_perfil_usuario_id_perfil_id_key ON public.usuario_perfil USING btree (usuario_id, perfil_id) WHERE (ativo IS TRUE);


--
-- Name: termo_contratual_old trg_termo_contratual_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_termo_contratual_updated_at BEFORE UPDATE ON public.termo_contratual_old FOR EACH ROW EXECUTE FUNCTION public.update_termo_contratual_updated_at();


--
-- Name: arquivo update_arquivo_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_arquivo_updated_at BEFORE UPDATE ON public.arquivo FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: configuracao_sistema update_configuracao_sistema_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_configuracao_sistema_updated_at BEFORE UPDATE ON public.configuracao_sistema FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: contratado update_contratado_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_contratado_updated_at BEFORE UPDATE ON public.contratado FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: contrato update_contrato_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_contrato_updated_at BEFORE UPDATE ON public.contrato FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: modalidade update_modalidade_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_modalidade_updated_at BEFORE UPDATE ON public.modalidade FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: password_reset_tokens update_password_reset_tokens_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_password_reset_tokens_updated_at BEFORE UPDATE ON public.password_reset_tokens FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: pendenciarelatorio update_pendenciarelatorio_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_pendenciarelatorio_updated_at BEFORE UPDATE ON public.pendenciarelatorio FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: perfil update_perfil_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_perfil_updated_at BEFORE UPDATE ON public.perfil FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: relatoriofiscal update_relatoriofiscal_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_relatoriofiscal_updated_at BEFORE UPDATE ON public.relatoriofiscal FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: status update_status_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_status_updated_at BEFORE UPDATE ON public.status FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: statuspendencia update_statuspendencia_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_statuspendencia_updated_at BEFORE UPDATE ON public.statuspendencia FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: statusrelatorio update_statusrelatorio_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_statusrelatorio_updated_at BEFORE UPDATE ON public.statusrelatorio FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: termo_aditivo update_termo_aditivo_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_termo_aditivo_updated_at BEFORE UPDATE ON public.termo_aditivo FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: usuario_perfil update_usuario_perfil_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_usuario_perfil_updated_at BEFORE UPDATE ON public.usuario_perfil FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: usuario update_usuario_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_usuario_updated_at BEFORE UPDATE ON public.usuario FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: arquivo arquivo_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.arquivo
    ADD CONSTRAINT arquivo_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contrato(id);


--
-- Name: audit_log audit_log_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id) ON DELETE CASCADE;


--
-- Name: contrato contrato_contratado_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato
    ADD CONSTRAINT contrato_contratado_id_fkey FOREIGN KEY (contratado_id) REFERENCES public.contratado(id);


--
-- Name: contrato contrato_fiscal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato
    ADD CONSTRAINT contrato_fiscal_id_fkey FOREIGN KEY (fiscal_id) REFERENCES public.usuario(id);


--
-- Name: contrato contrato_fiscal_substituto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato
    ADD CONSTRAINT contrato_fiscal_substituto_id_fkey FOREIGN KEY (fiscal_substituto_id) REFERENCES public.usuario(id);


--
-- Name: contrato contrato_gestor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato
    ADD CONSTRAINT contrato_gestor_id_fkey FOREIGN KEY (gestor_id) REFERENCES public.usuario(id);


--
-- Name: contrato contrato_modalidade_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato
    ADD CONSTRAINT contrato_modalidade_id_fkey FOREIGN KEY (modalidade_id) REFERENCES public.modalidade(id);


--
-- Name: contrato contrato_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato
    ADD CONSTRAINT contrato_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status(id);


--
-- Name: notification_log notification_log_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_log
    ADD CONSTRAINT notification_log_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contrato(id) ON DELETE CASCADE;


--
-- Name: ocorrencia ocorrencia_arquivo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencia
    ADD CONSTRAINT ocorrencia_arquivo_id_fkey FOREIGN KEY (arquivo_id) REFERENCES public.arquivo(id);


--
-- Name: ocorrencia ocorrencia_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencia
    ADD CONSTRAINT ocorrencia_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contrato(id);


--
-- Name: ocorrencia ocorrencia_fiscal_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencia
    ADD CONSTRAINT ocorrencia_fiscal_usuario_id_fkey FOREIGN KEY (fiscal_usuario_id) REFERENCES public.usuario(id);


--
-- Name: ocorrencia ocorrencia_relatorio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencia
    ADD CONSTRAINT ocorrencia_relatorio_id_fkey FOREIGN KEY (relatorio_id) REFERENCES public.relatoriofiscal(id);


--
-- Name: ocorrencia ocorrencia_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencia
    ADD CONSTRAINT ocorrencia_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status(id);


--
-- Name: ocorrencia ocorrencia_tipo_ocorrencia_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencia
    ADD CONSTRAINT ocorrencia_tipo_ocorrencia_id_fkey FOREIGN KEY (tipo_ocorrencia_id) REFERENCES public.tipo_ocorrencia(id);


--
-- Name: password_reset_tokens password_reset_tokens_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: pedidos pedidos_id_cliente_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_id_cliente_fkey FOREIGN KEY (id_cliente) REFERENCES public.clientes(id_cliente);


--
-- Name: pendenciarelatorio pendenciarelatorio_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pendenciarelatorio
    ADD CONSTRAINT pendenciarelatorio_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contrato(id);


--
-- Name: pendenciarelatorio pendenciarelatorio_criado_por_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pendenciarelatorio
    ADD CONSTRAINT pendenciarelatorio_criado_por_usuario_id_fkey FOREIGN KEY (criado_por_usuario_id) REFERENCES public.usuario(id);


--
-- Name: pendenciarelatorio pendenciarelatorio_status_pendencia_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pendenciarelatorio
    ADD CONSTRAINT pendenciarelatorio_status_pendencia_id_fkey FOREIGN KEY (status_pendencia_id) REFERENCES public.statuspendencia(id);


--
-- Name: relatorio_fiscalizacao relatorio_fiscalizacao_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatorio_fiscalizacao
    ADD CONSTRAINT relatorio_fiscalizacao_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contrato(id) ON DELETE CASCADE;


--
-- Name: relatoriofiscal relatoriofiscal_aprovador_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatoriofiscal
    ADD CONSTRAINT relatoriofiscal_aprovador_usuario_id_fkey FOREIGN KEY (aprovador_usuario_id) REFERENCES public.usuario(id);


--
-- Name: relatoriofiscal relatoriofiscal_arquivo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatoriofiscal
    ADD CONSTRAINT relatoriofiscal_arquivo_id_fkey FOREIGN KEY (arquivo_id) REFERENCES public.arquivo(id);


--
-- Name: relatoriofiscal relatoriofiscal_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatoriofiscal
    ADD CONSTRAINT relatoriofiscal_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contrato(id);


--
-- Name: relatoriofiscal relatoriofiscal_fiscal_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatoriofiscal
    ADD CONSTRAINT relatoriofiscal_fiscal_usuario_id_fkey FOREIGN KEY (fiscal_usuario_id) REFERENCES public.usuario(id);


--
-- Name: relatoriofiscal relatoriofiscal_pendencia_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatoriofiscal
    ADD CONSTRAINT relatoriofiscal_pendencia_id_fkey FOREIGN KEY (pendencia_id) REFERENCES public.pendenciarelatorio(id);


--
-- Name: relatoriofiscal relatoriofiscal_status_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relatoriofiscal
    ADD CONSTRAINT relatoriofiscal_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.statusrelatorio(id);


--
-- Name: session_context session_context_perfil_ativo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_context
    ADD CONSTRAINT session_context_perfil_ativo_id_fkey FOREIGN KEY (perfil_ativo_id) REFERENCES public.perfil(id);


--
-- Name: session_context session_context_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_context
    ADD CONSTRAINT session_context_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: termo_aditivo termo_aditivo_arquivo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.termo_aditivo
    ADD CONSTRAINT termo_aditivo_arquivo_id_fkey FOREIGN KEY (arquivo_id) REFERENCES public.arquivo(id);


--
-- Name: termo_aditivo termo_aditivo_contrato_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.termo_aditivo
    ADD CONSTRAINT termo_aditivo_contrato_id_fkey FOREIGN KEY (contrato_id) REFERENCES public.contrato(id);


--
-- Name: usuario_perfil usuario_perfil_concedido_por_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_perfil
    ADD CONSTRAINT usuario_perfil_concedido_por_usuario_id_fkey FOREIGN KEY (concedido_por_usuario_id) REFERENCES public.usuario(id);


--
-- Name: usuario usuario_perfil_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_perfil_id_fkey FOREIGN KEY (perfil_id) REFERENCES public.perfil(id);


--
-- Name: usuario_perfil usuario_perfil_perfil_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_perfil
    ADD CONSTRAINT usuario_perfil_perfil_id_fkey FOREIGN KEY (perfil_id) REFERENCES public.perfil(id);


--
-- Name: usuario_perfil usuario_perfil_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_perfil
    ADD CONSTRAINT usuario_perfil_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- PostgreSQL database dump complete
--

\unrestrict UPNCYsPfe49y4gufX2paYRv6Hzdx14efTlAv4s3EEoJLMGWs5UVdSvoLvISRP7G

