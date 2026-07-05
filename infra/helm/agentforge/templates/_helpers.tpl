{{/*
Common labels and helpers.
*/}}

{{- define "agentforge.labels" -}}
app.kubernetes.io/name: {{ .Values.appName | default "agentforge" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "agentforge.image" -}}
{{- $registry := .global.imageRegistry -}}
{{- $repo := printf "%s/%s" .Values.image.repository .component -}}
{{- if $registry -}}
{{ printf "%s/%s:%s" $registry $repo .Values.image.tag }}
{{- else -}}
{{ printf "%s:%s" $repo .Values.image.tag }}
{{- end -}}
{{- end }}

{{- define "agentforge.envFrom" -}}
envFrom:
  - configMapRef:
      name: {{ .Release.Name }}-config
  - secretRef:
      name: {{ .Release.Name }}-secrets
{{- end }}
